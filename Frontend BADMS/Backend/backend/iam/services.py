"""Identity, RBAC and directory — served from IAM's own tables.

Phase 1 of ADR-0014: `/me`, `/directory/users` and the RBAC lookups all hit
`system_db`, so the platform keeps working while the ERP is down.

The one exception is a login whose synced hash does not match, which falls
back to a live ERP read — otherwise a password reset in the ERP would not take
effect until the next sync. Best-effort: an unreachable ERP simply fails the
login, which is correct.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.db.models import Q
from django.utils import timezone

from iam.models import (IamDesignationModule, IamModule, IamToken, IamUser,
                        IamUserAcademic, IamUserDesignation, LoginAttempt,
                        RolePermission, SyncRun)

# Lockout ladder, counted per username. A success resets it.
LOCKOUT_TIERS = ((15, None), (10, 30), (8, 5), (5, 1))   # (failures, minutes)

# Hashing a dummy on unknown-user keeps response time from revealing existence.
_DUMMY_HASH = ("pbkdf2_sha256$260000$dummydummydummy$"
               "3S4l4tHZ4vJ8mQ0oK1qX9wY2zC5nB7dE8fG6hI0jK2M=")


class Locked(Exception):
    def __init__(self, minutes: int | None):
        self.minutes = minutes
        super().__init__("Account temporarily locked.")


# -- authentication ------------------------------------------------------------
def _recent_failures(username: str, within_minutes: int = 60) -> int:
    since = timezone.now() - timedelta(minutes=within_minutes)
    return (LoginAttempt.objects
            .filter(username=username, at__gte=since)
            .exclude(outcome="success").count())


def check_lockout(username: str) -> None:
    fails = _recent_failures(username)
    for threshold, minutes in LOCKOUT_TIERS:
        if fails >= threshold:
            if minutes is None:
                raise Locked(None)                     # needs an admin unlock
            last = (LoginAttempt.objects.filter(username=username)
                    .exclude(outcome="success").order_by("-at").first())
            if last and timezone.now() < last.at + timedelta(minutes=minutes):
                raise Locked(minutes)
            return
    return


def _verify(user: IamUser, password: str) -> bool:
    """Synced hash first; live ERP only if that fails."""
    if user.password_hash and check_password(password, user.password_hash):
        return True

    # The synced copy may be stale — e.g. the password was reset in the ERP
    # after the last sync. Try live, and refresh our copy if it works.
    try:
        from iam.sync import refresh_password_hash

        fresh = refresh_password_hash(user.username)
    except Exception:                                          # noqa: BLE001
        return False                                # ERP down: fail closed
    return bool(fresh) and check_password(password, fresh)


def authenticate(username: str, password: str, *, ip: str | None = None):
    """Verify credentials against the projection. Returns an IamToken or None.

    None covers both "no such user" and "wrong password" — the caller must not
    be able to distinguish them, or this becomes an enumeration oracle.
    """
    check_lockout(username)

    user = IamUser.objects.filter(username__iexact=username).first()
    if user is None:
        check_password(password, _DUMMY_HASH)       # equalise response time
        LoginAttempt.objects.create(username=username, ip=ip,
                                    outcome="unknown_user")
        return None

    if not user.is_active:
        check_password(password, _DUMMY_HASH)       # equalise response time
        LoginAttempt.objects.create(username=username, ip=ip, outcome="inactive")
        return None

    if not _verify(user, password):
        LoginAttempt.objects.create(username=username, ip=ip,
                                    outcome="bad_password")
        return None

    LoginAttempt.objects.create(username=username, ip=ip, outcome="success")
    _refresh_roles_if_stale(user)
    return IamToken.issue(erp_user_id=user.erp_user_id, username=user.username)


def _refresh_roles_if_stale(user: IamUser) -> None:
    """Re-read one person's posts, but only when the timer has fallen behind.

    Login is the wrong place to spend nine queries every time. With the sync
    timer running this row is minutes old and the refresh would find nothing,
    so it is skipped and login costs nothing extra. It happens only once the
    projection is older than the window it is meant to hold to — which is
    exactly when a post assigned today would otherwise be invisible.
    """
    after = getattr(settings, "IAM_REFRESH_ROLES_AFTER_SECONDS", 1800)
    if not after:
        return
    if user.synced_at and (timezone.now() - user.synced_at).total_seconds() < after:
        return

    from iam.sync import refresh_designations

    if refresh_designations(user.erp_user_id) is not None:
        # Stamped so a stalled sync does not make every login pay again.
        IamUser.objects.filter(pk=user.pk).update(synced_at=timezone.now())


def resolve_token(raw: str) -> IamToken | None:
    """Look up a session by its raw bearer value; the column holds a digest."""
    tok = IamToken.resolve(raw)
    if tok is None or not tok.is_live:
        return None
    tok.touch()
    return tok


# -- RBAC ----------------------------------------------------------------------
def designations_for(erp_user_id: int) -> list[str]:
    return sorted(IamUserDesignation.objects
                  .filter(erp_user_id=erp_user_id)
                  .values_list("designation", flat=True))


def modules_for(designations: Sequence[str]) -> list[str]:
    if not designations:
        return []
    return sorted(set(IamDesignationModule.objects
                      .filter(designation__in=list(designations))
                      .values_list("module_code", flat=True)))


def modules_by_designation(designations: Sequence[str]) -> dict[str, list[str]]:
    """Which modules each designation grants, separately.

    `modules_for` answers "may this person enter", which is the union. A shell
    that offers a role switcher needs the breakdown: a module granted to one of
    somebody's designations must not appear while they are acting as another.
    """
    if not designations:
        return {}
    out: dict[str, set[str]] = {d: set() for d in designations}
    rows = (IamDesignationModule.objects
            .filter(designation__in=list(designations))
            .values_list("designation", "module_code"))
    for designation, code in rows:
        out[designation].add(code)
    return {d: sorted(codes) for d, codes in out.items()}


def permissions_for(designations: Sequence[str]) -> list[str]:
    if not designations:
        return []
    return sorted(set(RolePermission.objects
                      .filter(designation__in=list(designations))
                      .values_list("permission", flat=True)))


def build_navigation(module_codes: Sequence[str],
                     permissions: Iterable[str]) -> list[dict]:
    """Navigation, already filtered and already in render shape.

    Spans every publisher, so one sidebar covers every Fusion app. The client
    does no filtering — it cannot draw a module the IAM did not send.
    """
    perms = set(permissions)
    granted = set(module_codes)
    if not granted:
        return []

    sections: dict[str, list[dict]] = {}
    modules = (IamModule.objects.filter(code__in=granted, status="active")
               .prefetch_related("nav_items"))

    for m in modules:
        items = [
            {"code": n.code, "label": n.label, "icon": n.icon, "to": n.to,
             "app": m.app}
            for n in m.nav_items.all()
            if not n.required_permission or n.required_permission in perms
        ]
        if not items:
            continue                     # a section that expands to nothing is worse
                                         # than no section at all
        entry = {"code": m.code, "label": m.label, "icon": m.icon, "app": m.app}
        if len(items) == 1 and items[0]["to"] == m.base_path:
            entry["to"] = items[0]["to"]     # single link — no pointless accordion
        else:
            entry["links"] = items
        sections.setdefault(m.nav_section, []).append(entry)

    # Two publishers can pick the same sort_order, so the tiebreak must be total.
    for items in sections.values():
        items.sort(key=lambda e: (e["app"], e["code"]))
    return [{"section": s, "items": v} for s, v in sorted(sections.items())]


def navigation_by_designation(designations: Sequence[str]) -> dict[str, list[dict]]:
    """Each designation's own sidebar, built from that designation alone.

    The union would leak: somebody who is both a student and an office holder
    would see the student's own screens while acting as the office, because the
    module is granted to both and the items were filtered against every
    permission they hold rather than the ones the acting role carries.
    """
    modules = modules_by_designation(designations)
    return {d: build_navigation(modules.get(d, []), permissions_for([d]))
            for d in designations}


def build_session(token: IamToken) -> dict:
    """The /me payload. Four queries against system_db, zero against the ERP."""
    user = IamUser.objects.filter(erp_user_id=token.erp_user_id).first()
    if user is None or not user.is_active:
        return {}

    # The basic role is held by definition, not assigned. The ERP records it as
    # extrainfo.user_type and has no designation row for it, so a grant written
    # against `faculty` would otherwise reach nobody, and the 121 staff who hold
    # no designation at all would have no role whatsoever.
    roles = designations_for(user.erp_user_id)
    if user.kind not in roles:
        roles = [user.kind, *roles]

    modules = modules_for(roles)
    permissions = permissions_for(roles)
    payload = {
        "user": {
            "id": user.erp_user_id,
            "username": user.username,
            "display_name": user.display_name or user.username,
            "kind": user.kind,
            "email": user.email,
        },
        "basic_role": user.kind,
        # Their own choice if it still holds, else an office outranks the basic role.
        "active_role": (user.last_selected_role
                        if user.last_selected_role in roles
                        else next((r for r in roles if r != user.kind), user.kind)),
        "roles": roles,
        "permissions": permissions,
        "modules": modules,
        # The same grants split by designation, for a shell with a role switcher.
        "modules_by_role": modules_by_designation(roles),
        # Spans every publisher, so one app can draw the whole sidebar.
        "navigation": build_navigation(modules, permissions),
        # The same sidebar split by designation, for a shell with a role switcher.
        "navigation_by_role": navigation_by_designation(roles),
        "identity_synced_at": user.synced_at.isoformat(),
    }
    if user.kind == "student":
        # Absent, not null, when no result is declared — so a consumer that
        # forgets to check gets a KeyError rather than a silent zero.
        standing = IamUserAcademic.objects.filter(
            erp_user_id=user.erp_user_id).first()
        if standing is not None:
            payload["academic"] = _academic_row(standing)
    return payload


# -- directory -----------------------------------------------------------------
def _to_row(u: IamUser) -> dict:
    return {
        "user_id": u.erp_user_id,
        "username": u.username,
        "display_name": u.display_name or u.username,
        "kind": u.kind,
        "email": u.email,
        "department": u.department,
        "programme": u.programme,
        "discipline": u.discipline,
        "batch_year": u.batch_year,
        # Consumers act on their projection, so it must be able to retire an account.
        "is_active": u.is_active,
        # Maintained on the portal's profile page; read, never written, here.
        "resume_link": u.resume_link,
        "profile_completed": u.profile_completed,
    }


def directory_users(erp_user_ids: Sequence[int]) -> list[dict]:
    """Batched. One query, regardless of how many ids are asked for."""
    ids = {int(i) for i in erp_user_ids if i is not None}
    if not ids:
        return []
    return [_to_row(u) for u in
            IamUser.objects.filter(erp_user_id__in=ids).order_by("erp_user_id")]


def search_directory(q: str = "", kind: str | None = None,
                     limit: int = 25) -> list[dict]:
    qs = IamUser.objects.filter(is_active=True)
    if kind:
        qs = qs.filter(kind=kind)
    if q:
        qs = qs.filter(username__icontains=q)
    return [_to_row(u) for u in qs.order_by("username")[:limit]]


def employee_page(limit: int = 500, offset: int = 0) -> dict:
    """Every employee, a page at a time."""
    qs = IamUser.objects.filter(is_active=True, kind__in=("faculty", "staff"))
    total = qs.count()
    rows = qs.order_by("erp_user_id")[offset:offset + limit]
    return {
        "count": total,
        "limit": limit,
        "offset": offset,
        "results": [_to_row(u) for u in rows],
    }


# -- academic standing (declared CPI) ------------------------------------------
def _academic_row(a: IamUserAcademic) -> dict:
    return {
        "user_id": a.erp_user_id,
        "roll_no": a.roll_no,
        "cpi": str(a.cpi),
        "earned_credits": str(a.earned_credits),
        "active_backlogs": a.active_backlogs,
        "semester": a.semester,
        "semester_type": a.semester_type,
        "declared_seq": a.declared_seq,
        "programme": a.programme,
        # Provenance travels with the number. A CPI rendered without its
        # semester and freshness is what starts the "my CPI is wrong" queue.
        "computed_by": a.computed_by,
        "synced_at": a.synced_at.isoformat(),
    }


def academic_standings(erp_user_ids: Sequence[int]) -> list[dict]:
    """Batched, like the directory. A student with no DECLARED result is simply
    absent — callers must treat absence as ineligible, never as zero."""
    ids = {int(i) for i in erp_user_ids if i is not None}
    if not ids:
        return []
    return [_academic_row(a) for a in
            IamUserAcademic.objects.filter(erp_user_id__in=ids)
            .order_by("erp_user_id")]


def academic_directory(*, q: str = "", discipline: str = "",
                       batch_year: int | None = None, programme: str = "",
                       only_declared: bool = False,
                       limit: int = 50, offset: int = 0) -> dict:
    """Browse every student's declared standing, filtered and paginated.

    Where `academic_standings(ids)` answers "what is the CPI of these people",
    this answers "who is there" — the whole cohort's academic record, so the
    caller must be placement staff.

    A student with no declared result is still LISTED, with `cpi: null`: the
    placement office needs to see who is missing one, and omitting them makes
    an undeclared batch look like an empty one.
    """
    users = IamUser.objects.filter(kind="student", is_active=True)
    if discipline:
        users = users.filter(discipline__iexact=discipline)
    if batch_year:
        users = users.filter(batch_year=batch_year)
    if programme:
        users = users.filter(programme__iexact=programme)
    if q:
        users = users.filter(
            Q(username__icontains=q) | Q(display_name__icontains=q))
    if only_declared:
        # Narrow the QUERY, not the page: filtering after slicing reports the
        # unfiltered count and empties any page whose rows are undeclared.
        users = users.filter(
            erp_user_id__in=IamUserAcademic.objects.values("erp_user_id"))

    total = users.count()
    page = list(users.order_by("username")[offset:offset + limit])

    # One extra query for the whole page, not one per student.
    standings = {
        a.erp_user_id: a for a in
        IamUserAcademic.objects.filter(
            erp_user_id__in=[u.erp_user_id for u in page])
    }

    return {
        "count": total,
        "limit": limit,
        "offset": offset,
        "results": [
            {
                "user_id": u.erp_user_id,
                "roll_no": u.username,
                "name": u.display_name or u.username,
                "discipline": u.discipline,
                "programme": u.programme,
                "batch_year": u.batch_year,
                **(_academic_row(standings[u.erp_user_id])
                   if u.erp_user_id in standings
                   else {"cpi": None, "earned_credits": None,
                         "active_backlogs": None, "semester": None,
                         "semester_type": None, "declared_seq": None,
                         "computed_by": None, "synced_at": None}),
            }
            for u in page
        ],
    }


def academic_filters() -> dict:
    """The distinct values worth offering as filters, so the UI never has to
    hard-code a discipline list that will go stale."""
    base = IamUser.objects.filter(kind="student", is_active=True)
    return {
        "disciplines": sorted(
            d for d in base.values_list("discipline", flat=True).distinct() if d),
        "batch_years": sorted(
            (b for b in base.values_list("batch_year", flat=True).distinct()
             if b), reverse=True),
        "programmes": sorted(
            p for p in base.values_list("programme", flat=True).distinct() if p),
    }


def identity_freshness() -> dict:
    """How stale is the projection? Surfaced on /readyz and worth alerting on."""
    last = SyncRun.objects.filter(status="succeeded").first()
    if last is None:
        return {"synced": False, "age_seconds": None, "users": 0}
    return {
        "synced": True,
        "age_seconds": int((timezone.now() - last.finished_at).total_seconds()),
        "users": IamUser.objects.filter(is_active=True).count(),
    }
