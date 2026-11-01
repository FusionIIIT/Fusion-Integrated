"""The ERP -> IAM projection. One-way, idempotent, batched.

Phase 1 of ADR-0014: the ERP stays the source of truth, and IAM keeps a copy so
that serving a request never requires the ERP to be reachable.

Idempotent by construction — every write is an upsert keyed on a natural key,
so running it twice changes nothing and a half-finished run is safe to repeat.
"""
from __future__ import annotations

import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from iam import erp_source, rbac
from iam.models import (IamRoleViolation, IamUser, IamUserAcademic,
                        IamUserDesignation, SyncRun)

log = logging.getLogger("fusion.iam.sync")

USER_FIELDS = ["username", "display_name", "email", "kind", "is_active",
               "password_hash", "department", "programme", "discipline",
               "batch_year", "resume_link", "profile_completed", "synced_at"]

# Stamped onto every academic row. Bump the version when iam/grades.py changes
# so a stale CPI is identifiable after the fact rather than indistinguishable.
COMPUTED_BY = "iam-replica/v1"


#: A run that would retire more than this share of the people it just read is
#: treated as a bad read, not as 1,500 resignations. Overridable per run.
MAX_DEACTIVATION_SHARE = 0.02
#: Below this, share is meaningless — a small ERP legitimately loses a few.
DEACTIVATION_FLOOR = 25


class SuspectDeactivation(RuntimeError):
    """Raised instead of deactivating implausibly many users at once."""


def _guard_deactivation(doomed: int, seen: int, *, force: bool) -> None:
    """Refuse a mass deactivation that looks like a truncated read.

    `seen` being non-empty is not evidence the read was complete: a filter that
    silently drops rows, a LIMIT, or a join that loses a table leaves a partial
    set, and everyone missing from it would be locked out on the next login.
    The failure is invisible until people ring up, so it fails loudly here.
    """
    if force or doomed <= DEACTIVATION_FLOOR:
        return
    if doomed <= (seen + doomed) * MAX_DEACTIVATION_SHARE:
        return
    raise SuspectDeactivation(
        f"{doomed} of {seen + doomed} users would be deactivated, over the "
        f"{MAX_DEACTIVATION_SHARE:.0%} limit. The ERP read is more likely "
        f"truncated than that many people having left. Re-run with "
        f"--force-deactivate if it is genuine.")


def sync_all(*, batch_size: int = 500, deactivate_missing: bool = True,
             force_deactivate: bool = False) -> SyncRun:
    """Project every ERP user, designation and academic standing into IAM.

    Module grants are not projected: they are published by each service's
    manifest and seeded by seed_iam_permissions, so the ERP has no say.
    """
    run = SyncRun.objects.create()
    try:
        seen: set[int] = set()
        written = 0

        profiles = erp_source.all_student_profiles()
        for batch in erp_source.iter_users(batch_size=batch_size):
            for r in batch:
                r.update(profiles.get(r["erp_user_id"], {}))
            rows = [IamUser(**r) for r in batch]
            run.usernames_released += _release_usernames(batch)
            IamUser.objects.bulk_create(
                rows, update_conflicts=True,
                unique_fields=["erp_user_id"], update_fields=USER_FIELDS,
            )
            seen.update(r["erp_user_id"] for r in batch)
            written += len(rows)

        run.users_seen = len(seen)
        run.users_written = written

        with transaction.atomic(using="system_db"):
            run.role_violations = _replace_designations(
                [*erp_source.all_user_designations(),
                 # Derived, not held: what someone is studying decides which
                 # student-facing permissions reach them, and the ERP records
                 # "student" for all 3,027 regardless of programme.
                 *erp_source.all_student_programme_roles()], run)
            run.academics_written = _replace_academics(
                erp_source.all_academic_standings())

        if deactivate_missing and seen:
            # A user who vanished from the ERP is deactivated, never deleted:
            # placement applications and audit rows reference the id, and a
            # hard delete would leave them dangling.
            doomed = (IamUser.objects
                      .exclude(erp_user_id__in=seen)
                      .filter(is_active=True))
            _guard_deactivation(doomed.count(), len(seen), force=force_deactivate)
            run.deactivated = doomed.update(is_active=False)

        run.status = "succeeded"
    except Exception as exc:                                   # noqa: BLE001
        run.status = "failed"
        run.error = f"{exc.__class__.__name__}: {exc}"
        log.exception("iam.sync.failed")
        raise
    finally:
        run.finished_at = timezone.now()
        run.save()
    return run


def _replace_designations(pairs: list[tuple[int, str]], run: SyncRun) -> int:
    """Replace wholesale rather than diff, checking the role policy on the way.

    A designation being *removed* is the security-relevant change, and a diff
    that only adds would silently keep revoked roles alive. Wholesale replace
    inside a transaction cannot get that wrong.

    The policy check happens here because here is where the ERP's answer becomes
    IAM's answer. A role its holder's basic role may not hold is always recorded;
    it is only withheld when IAM_ENFORCE_ROLE_POLICY is on. Returns the violation
    count; run.designations_written is set as a side effect.
    """
    identity = dict(IamUser.objects.values_list("erp_user_id", "kind"))
    usernames = dict(IamUser.objects.values_list("erp_user_id", "username"))
    found = rbac.violations(pairs, identity, usernames)
    enforcing = getattr(settings, "IAM_ENFORCE_ROLE_POLICY", False)
    allowed = rbac.exceptions()

    # Recorded either way: an exception nobody remembers must stay visible.
    refused = {(v["erp_user_id"], v["designation"]) for v in found
               if enforcing
               and (v["username"], v["designation"]) not in allowed}

    IamUserDesignation.objects.all().delete()
    rows = [IamUserDesignation(erp_user_id=uid, designation=name)
            for uid, name in set(pairs) if (uid, name) not in refused]
    IamUserDesignation.objects.bulk_create(rows, batch_size=1000)

    IamRoleViolation.objects.all().delete()
    IamRoleViolation.objects.bulk_create(
        [IamRoleViolation(
            enforced=(v["erp_user_id"], v["designation"]) in refused, **v)
         for v in found],
        batch_size=1000)

    run.designations_written = len(rows)
    return len(found)


def _release_usernames(batch: list[dict]) -> int:
    """Free a username the ERP has moved to a different account.

    An account deleted and recreated upstream keeps its username but gets a new
    id. Upserting on erp_user_id leaves the old row holding that username, and
    the unique index then rejects the new one — the whole sync dies on one row.

    The stale holder is retired, never deleted: placement applications and audit
    trails reference its id, and a hard delete would leave them dangling.
    """
    wanted = {r["username"]: r["erp_user_id"] for r in batch if r.get("username")}
    if not wanted:
        return 0
    stale = (IamUser.objects.filter(username__in=wanted)
             .exclude(erp_user_id__in=wanted.values()))
    released = 0
    for holder in stale:
        log.warning("iam.sync.username_moved username=%s from=%s to=%s",
                    holder.username, holder.erp_user_id, wanted[holder.username])
        holder.username = f"retired:{holder.erp_user_id}:{holder.username}"[:150]
        holder.is_active = False
        holder.save(update_fields=["username", "is_active"])
        released += 1
    return released


def _replace_academics(standings: list[dict]) -> int:
    """Wholesale replace, for the same reason as designations.

    A result being RETRACTED is the case that matters: the student's row must
    disappear so eligibility fails closed again. A diff that only upserts would
    leave a retracted CPI in place, and someone would apply on it.

    Rows are keyed by roll_no in the ERP but by erp_user_id here, so the join
    back to identity happens once, in bulk.
    """
    user_by_roll = dict(IamUser.objects.values_list("username", "erp_user_id"))
    # Roll number and username are the same string for students, but compare
    # case-insensitively — the ERP is inconsistent about case in places.
    lower = {k.lower(): v for k, v in user_by_roll.items()}

    rows = []
    for s in standings:
        uid = user_by_roll.get(s["roll_no"]) or lower.get(s["roll_no"].lower())
        if uid is None:
            continue                      # a grade row with no matching user
        rows.append(IamUserAcademic(
            erp_user_id=uid, roll_no=s["roll_no"],
            cpi=s["cpi"], earned_credits=s["earned_credits"],
            cpi_denominator_credits=s["cpi_denominator_credits"],
            active_backlogs=s["active_backlogs"],
            courses_counted=s["courses_counted"],
            semester=s["semester"], semester_type=s["semester_type"],
            declared_seq=s["declared_seq"],
            erp_announcement_id=s["announcement_id"],
            programme=s["programme"], computed_by=COMPUTED_BY,
        ))

    IamUserAcademic.objects.all().delete()
    IamUserAcademic.objects.bulk_create(rows, batch_size=1000)
    return len(rows)


def refresh_password_hash(username: str) -> str | None:
    """Re-pull one user's hash after a live-ERP fallback succeeded.

    Keeps the copy correct without waiting for the next full sync.
    """
    fresh = erp_source.fetch_password_hash(username)
    if fresh:
        IamUser.objects.filter(username__iexact=username).update(
            password_hash=fresh, synced_at=timezone.now())
    return fresh


def refresh_designations(erp_user_id: int) -> int | None:
    """Re-pull one user's designations, live.

    A password changed in the ERP takes effect at the next login because the
    hash check falls back to a live read. A designation had no such path, so a
    post assigned this morning stayed invisible to every service until somebody
    remembered to run the sync. Called at login, which is both the moment the
    answer matters and rare enough to afford two ERP queries.

    Returns the number of designations now held, or None if the ERP could not
    be read — the caller keeps the projection it already has, which is the same
    behaviour as never having asked.
    """
    try:
        pairs = erp_source.designations_for_user(erp_user_id)
    except Exception:                                          # noqa: BLE001
        log.exception("iam.sync.refresh_designations_failed uid=%s", erp_user_id)
        return None

    identity = dict(IamUser.objects.filter(erp_user_id=erp_user_id)
                    .values_list("erp_user_id", "kind"))
    usernames = dict(IamUser.objects.filter(erp_user_id=erp_user_id)
                     .values_list("erp_user_id", "username"))
    found = rbac.violations(pairs, identity, usernames)
    enforcing = getattr(settings, "IAM_ENFORCE_ROLE_POLICY", False)
    allowed = rbac.exceptions()
    refused = {(v["erp_user_id"], v["designation"]) for v in found
               if enforcing
               and (v["username"], v["designation"]) not in allowed}

    rows = [IamUserDesignation(erp_user_id=uid, designation=name)
            for uid, name in set(pairs) if (uid, name) not in refused]
    with transaction.atomic(using="system_db"):
        # Replaced wholesale for the same reason the full sync does it: a
        # designation taken away is the change that matters.
        IamUserDesignation.objects.filter(erp_user_id=erp_user_id).delete()
        IamUserDesignation.objects.bulk_create(rows)
    return len(rows)
