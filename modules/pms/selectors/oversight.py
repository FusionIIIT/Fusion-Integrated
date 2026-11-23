"""Queues and oversight: what waits on whom (UC-PMS-016, 027, 032; PMS-AFR-057, 064)."""
from __future__ import annotations

from django.db.models import Count, Exists, OuterRef, Subquery
from django.utils import timezone

from modules.pms.domain import state_machine as sm
from modules.pms.models import (
    Appeal,
    Application,
    AttorneyAssignment,
    Budget,
    Escalation,
    LicensingRequest,
    MaintenanceCycle,
    OfficeAction,
    ReviewCycle,
)
from modules.pms.selectors import scoping


def _latest_director():
    return Subquery(ReviewCycle.objects.filter(application=OuterRef("application"))
                    .order_by("-cycle_no").values("director_user_id")[:1])


def awaiting_director():
    return (Application.objects.filter(status__in=sorted(sm.AWAITING_DIRECTOR))
            .order_by("submitted_at", "id"))


def awaiting_attorney():
    """PMS-AFR-064: approved applications with no live attorney assignment."""
    live = AttorneyAssignment.objects.filter(application=OuterRef("pk"),
                                             status__in=sorted(sm.LIVE_ASSIGNMENT))
    return (Application.objects.filter(status__in=sorted(sm.ATTORNEY_ASSIGNABLE))
            .exclude(Exists(live)).order_by("updated_at", "id"))


def _items(qs, kind: str, label) -> list[dict]:
    return [{"kind": kind, **label(o)} for o in qs]


def _app_label(a: Application) -> dict:
    return {"id": a.pk, "application_id": a.pk, "reference": a.reference or "",
            "title": a.title, "status": a.status}


def _rel_label(o) -> dict:
    a = o.application
    return {"id": o.pk, "application_id": a.pk, "reference": a.reference or "",
            "title": a.title, "status": o.status}


def my_work(actor) -> list[dict]:
    """The actor's pending items; each kind is one query."""
    who, uid = scoping.lane(actor), getattr(actor, "user_id", None)
    items: list[dict] = []
    if who == scoping.APPLICANT:
        mine = Application.objects.filter(applicant_user_id=uid)
        items += _items(mine.filter(status=sm.DRAFT), "draft", _app_label)
        items += _items(mine.filter(status__in=sorted(sm.REVISABLE)), "revision", _app_label)
        items += _items(OfficeAction.objects.select_related("application").filter(
            application__applicant_user_id=uid, status=sm.AWAITING_APPLICANT),
            "office_action_approval", _rel_label)
    elif who == scoping.DIRECTOR:
        items += _items(ReviewCycle.objects.select_related("application").filter(
            director_user_id=uid, status="open"), "review", _rel_label)
        items += _items(Appeal.objects.select_related("application").filter(
            director_user_id=uid, status=sm.APPEAL_OPEN), "appeal", _rel_label)
        items += _items(Budget.objects.select_related("application")
                        .annotate(decider=_latest_director())
                        .filter(status=sm.PROPOSED, decider=uid), "budget", _rel_label)
        items += _items(MaintenanceCycle.objects.select_related("application").filter(
            deciding_director_user_id=uid, status=sm.DECISION_REQUESTED),
            "renewal", _rel_label)
        items += _items(LicensingRequest.objects.select_related("application").filter(
            routed_director_user_id=uid).exclude(status=sm.AGREEMENT_RECORDED),
            "licensing", _rel_label)
    elif who == scoping.ATTORNEY:
        items += _items(AttorneyAssignment.objects.select_related("application").filter(
            attorney_user_id=uid, status__in=sorted(sm.LIVE_ASSIGNMENT)), "case", _rel_label)
    elif who == scoping.ADMIN:
        items += _items(awaiting_director(), "assign_director", _app_label)
        items += _items(awaiting_attorney(), "assign_attorney", _app_label)
        items += _items(Budget.objects.select_related("application").filter(
            status__in=[sm.ESCALATED, sm.ESCALATION_TRACKED]), "escalated_budget", _rel_label)
        items += _items(Escalation.objects.select_related("application").filter(
            status="open"), "escalation", _rel_label)
        items += _items(LicensingRequest.objects.select_related("application").filter(
            status=sm.LICENSING_SUBMITTED), "licensing_unrouted", _rel_label)
    return items


def workflow_summary(actor) -> dict:
    """UC-PMS-032: counts by status within scope, and what is pending."""
    apps = scoping.applications_for(actor)
    by_status = dict(apps.values_list("status").annotate(n=Count("id")))
    overdue_reviews = ReviewCycle.objects.filter(application__in=apps, status="open",
                                                 due_on__lt=timezone.localdate()).count()
    return {"by_status": {s: by_status.get(s, 0) for s in sm.APPLICATION_STATUSES},
            "total": sum(by_status.values()),
            "overdue_reviews": overdue_reviews,
            "open_escalations": Escalation.objects.filter(application__in=apps,
                                                          status="open").count()}
