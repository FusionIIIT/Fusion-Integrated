"""Report rows, always built from the caller's own scope (BR-PMS-003, 005; UC-PMS-024, 030, 031)."""
from __future__ import annotations

from collections import defaultdict
from datetime import date

from django.db.models import Count, Q, QuerySet
from django.db.models.functions import TruncMonth
from django.utils import timezone

from modules.directory import contracts as directory
from modules.pms.domain import state_machine as sm
from modules.pms.models import (
    Application,
    AttorneyAssignment,
    AuditEntry,
    Budget,
    Escalation,
    Inventor,
    ReviewCycle,
)
from modules.pms.selectors import deadlines, scoping

HISTORY_STATES = (sm.SUBMITTED, sm.APPROVED, sm.REJECTED, sm.FILED, sm.GRANTED)


def report_scope(actor) -> QuerySet[Application]:
    """An applicant's reports cover only applications they made, not ones they co-invented."""
    apps = scoping.applications_for(actor)
    if scoping.lane(actor) == scoping.APPLICANT:
        apps = apps.filter(applicant_user_id=actor.user_id)
    return apps


def _filtered(apps: QuerySet[Application], filters: dict) -> QuerySet[Application]:
    if filters.get("status"):
        apps = apps.filter(status=filters["status"])
    if filters.get("domain_code"):
        apps = apps.filter(domain_code=filters["domain_code"])
    if filters.get("date_from"):
        apps = apps.filter(created_at__date__gte=filters["date_from"])
    if filters.get("date_to"):
        apps = apps.filter(created_at__date__lte=filters["date_to"])
    return apps


def _names(user_ids) -> dict[int, str]:
    ids = [u for u in user_ids if u is not None]
    people = directory.get_users(ids) if ids else {}
    return {u: (people[u].display_name if u in people else f"User {u}") for u in ids}


def _status(apps, _actor) -> list[dict]:
    return [{"reference": a.reference or "", "title": a.title, "status": a.status,
             "domain_code": a.domain_code,
             "submitted_at": a.submitted_at.isoformat() if a.submitted_at else "",
             "updated_at": a.updated_at.isoformat()}
            for a in apps.order_by("-updated_at", "-id")]


def _financial(apps, _actor) -> list[dict]:
    return [{"reference": b.application.reference or "", "title": b.application.title,
             "budget_status": b.status, "filing_fee": str(b.filing_fee),
             "attorney_fee": str(b.attorney_fee), "admin_cost": str(b.admin_cost),
             "total": str(b.total)}
            for b in Budget.objects.select_related("application")
            .filter(application__in=apps).order_by("-id")]


def _deadlines(apps, _actor) -> list[dict]:
    rows = deadlines.tracked(apps)
    names = _names({r.responsible_user_id for r in rows})
    today = timezone.localdate()
    return [{"reference": r.reference or "", "kind": r.kind, "due_on": r.due_on.isoformat(),
             "days_left": (r.due_on - today).days,
             "responsible": names.get(r.responsible_user_id, "")} for r in rows]


def _inventors(apps, _actor) -> list[dict]:
    return [{"reference": i.application.reference or "", "title": i.application.title,
             "inventor": i.name, "share_percent": str(i.share_percent),
             "agreement": "complete" if i.agreement_completed_at else "pending",
             "consent": "recorded" if i.consent_recorded_at else "pending"}
            for i in Inventor.objects.select_related("application")
            .filter(application__in=apps).order_by("application_id", "id")]


def _portfolio(apps, _actor) -> list[dict]:
    return [{"domain_code": r["domain_code"], "status": r["status"], "count": r["n"]}
            for r in apps.values("domain_code", "status").annotate(n=Count("id"))
            .order_by("domain_code", "status")]


def _workload(apps, actor) -> list[dict]:
    """A Director sees only their own workload; PCC_ADMIN sees everyone's (BR-PMS-005)."""
    reviews = ReviewCycle.objects.filter(status="open")
    cases = AttorneyAssignment.objects.filter(status__in=sorted(sm.LIVE_ASSIGNMENT))
    if scoping.lane(actor) != scoping.ADMIN:
        reviews = reviews.filter(director_user_id=actor.user_id)
        cases = cases.none()
    director_load = dict(reviews.values_list("director_user_id").annotate(n=Count("id")))
    attorney_load = dict(cases.values_list("attorney_user_id").annotate(n=Count("id")))
    names = _names(set(director_load) | set(attorney_load))
    rows = [{"person": names[u], "role": "Director", "open_items": n}
            for u, n in sorted(director_load.items())]
    rows += [{"person": names[u], "role": "Attorney", "open_items": n}
             for u, n in sorted(attorney_load.items())]
    return rows


def _dashboard(apps, actor) -> list[dict]:
    counts = dict(apps.values_list("status").annotate(n=Count("id")))
    today = timezone.localdate()
    rows = [{"measure": "Applications", "value": sum(counts.values())}]
    rows += [{"measure": s.replace("_", " ").capitalize(), "value": counts.get(s, 0)}
             for s in (sm.SUBMITTED, sm.UNDER_REVIEW, sm.APPROVED, sm.FILED, sm.GRANTED)]
    rows.append({"measure": "Overdue deadlines",
                 "value": sum(1 for r in deadlines.tracked(apps) if r.due_on < today)})
    if scoping.lane(actor) == scoping.ADMIN:
        rows.append({"measure": "Open escalations",
                     "value": Escalation.objects.filter(status="open").count()})
    return rows


def _monthly(apps) -> dict[date, dict[str, int]]:
    rows = (AuditEntry.objects.filter(application__in=apps, to_state__in=HISTORY_STATES)
            .exclude(Q(from_state="") | Q(action__startswith="report"))
            .annotate(month=TruncMonth("at")).values("month", "to_state")
            .annotate(n=Count("id")))
    out: dict[date, dict[str, int]] = defaultdict(dict)
    for r in rows:
        out[r["month"].date() if hasattr(r["month"], "date") else r["month"]][r["to_state"]] = \
            r["n"]
    return dict(sorted(out.items()))


def _history(apps, _actor) -> list[dict]:
    return [{"month": m.strftime("%Y-%m"), **{s: v.get(s, 0) for s in HISTORY_STATES}}
            for m, v in _monthly(apps).items()]


def _trend(apps, _actor) -> list[dict]:
    rows, previous = [], None
    for m, v in _monthly(apps).items():
        n = v.get(sm.SUBMITTED, 0)
        rows.append({"month": m.strftime("%Y-%m"), "submitted": n,
                     "change": "" if previous is None else n - previous})
        previous = n
    return rows


BUILDERS = {"status": _status, "financial": _financial, "deadlines": _deadlines,
            "inventors": _inventors, "portfolio": _portfolio, "workload": _workload,
            "dashboard": _dashboard, "history": _history, "trend": _trend}


def report_rows(actor, report_type: str, filters: dict, columns: tuple[str, ...]) -> list[dict]:
    apps = _filtered(report_scope(actor), filters)
    return [{c: row.get(c, "") for c in columns} for row in BUILDERS[report_type](apps, actor)]
