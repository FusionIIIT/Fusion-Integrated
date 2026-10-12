"""Resumption of duty after EL/COL/VL (EL-UC-010, EL-UC-011, BR-EL-027/028).

Two rules carry the whole shape of this module:

  * no adjustment happens before the review — the employee declaring a return
    date is not the same act as the institute accepting it;
  * normal, early and late return differ only by *what is synchronised*. There
    is deliberately no generic "closed" status (BR-EL-028, CW-EL-04 note).
"""
from __future__ import annotations

import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.leave.domain import categories as cat
from modules.leave.domain import counting, eligibility, routing
from modules.leave.domain import state_machine as sm
from modules.leave.models import LeaveRequest, LeaveResumption, WorkflowTask
from modules.leave.selectors import leave as sel
from modules.leave.services import accounts, authz, facts, notifications

log = logging.getLogger("fusion.leave.resumption")

TASK_CLASS = "resumption.review"


def _sanction_role(request) -> str:
    route = [routing.Step(order=int(s["order"]), kind=s["kind"],
                          authority=s.get("authority", ""))
             for s in (request.route or [])]
    step = routing.sanction_step(route)
    employee = facts.employee(request.user_id)
    return routing.role_for_step(
        step or routing.Step(order=99, kind=routing.SANCTION,
                             authority=routing.DEFAULT_AUTHORITY),
        unit=employee.unit if employee else "")


@transaction.atomic
def submit(*, actor, request_id: int, actual_date, remarks: str = ""
           ) -> LeaveResumption:
    """EL-UC-010 — record the actual return and route it for review."""
    authz.require(actor, sm.P_APPLY)
    request = (LeaveRequest.objects.select_for_update().filter(pk=request_id)
               .first())
    if request is None:
        raise NotFoundError("No such leave record.")
    authz.require_owner(actor, request)

    problem = eligibility.resumption_window(category=request.category)
    if problem:
        raise ConflictError(problem.message, code=problem.code,
                            details=[problem.details] if problem.details else [])
    if request.status not in (sm.APPROVED, sm.EXTENDED):
        raise ConflictError("Only an approved leave can be resumed.",
                            code="leave_not_approved")
    if actual_date < request.period_from:
        raise ConflictError(
            "The actual resumption date cannot precede the leave start.",
            code="resumption_before_start",
            details=[{"period_from": request.period_from.isoformat()}])
    if sel.pending_resumption_for_request(request.pk) is not None:
        raise ConflictError("A resumption for this leave is already under review.",
                            code="resumption_already_submitted")

    resumption = LeaveResumption.objects.create(
        request=request, user_id=request.user_id, actual_date=actual_date,
        remarks=remarks[:300], submitted_at=timezone.now())
    WorkflowTask.objects.create(
        request=request, step_order=98, step_kind=routing.SANCTION,
        task_class=TASK_CLASS, assignee_role=_sanction_role(request))
    notifications.enqueue(
        topic="leave.resumption.submitted",
        dedupe_key=f"leave.resumption:{resumption.pk}:submitted",
        recipient_user_id=None,
        subject=f"Resumption awaiting review — {request.reference}",
        body=(f"Actual resumption {actual_date} was submitted for leave "
              f"{request.period_from} to {request.period_to}."),
        payload={"request_id": request.pk, "resumption_id": resumption.pk})
    return resumption


def _reviewer_may_act(actor, resumption) -> None:
    """The applicable Sanctioning Authority reviews it (BR-EL-027)."""
    authz.require(actor, sm.P_DECIDE)
    open_task = (WorkflowTask.objects
                 .filter(request_id=resumption.request_id, task_class=TASK_CLASS,
                         status="pending").order_by("-id").first())
    if open_task is None:
        raise ConflictError("This resumption is no longer awaiting review.",
                            code="resumption_not_pending")
    if not authz.may_act(actor, open_task):
        raise PermissionDeniedError("This resumption is not yours to review.",
                                    code="not_your_review")


@transaction.atomic
def review(*, actor, resumption_id: int, note: str = "") -> LeaveResumption:
    """EL-UC-011 / BR-EL-028 — apply only the adjustment the actual date needs."""
    resumption = (LeaveResumption.objects.select_related("request")
                  .filter(pk=resumption_id).first())
    if resumption is None:
        raise NotFoundError("No such resumption submission.")
    if resumption.outcome != "pending":
        raise ConflictError("That resumption has already been reviewed.",
                            code="already_reviewed")
    _reviewer_may_act(actor, resumption)

    request = LeaveRequest.objects.select_for_update().get(pk=resumption.request_id)
    approved_end = request.period_to
    actual = resumption.actual_date

    if actual == approved_end:
        outcome = "no_adjustment"
    elif actual < approved_end:
        outcome = "early"
        _sync_early(request=request, actual=actual)
    else:
        outcome = "late"
        _sync_late(request=request, actual=actual)

    resumption.outcome = outcome
    resumption.reviewed_at = timezone.now()
    resumption.reviewed_by_user_id = getattr(actor, "user_id", None)
    resumption.review_note = note[:300]
    resumption.save(update_fields=["outcome", "reviewed_at", "reviewed_by_user_id",
                                   "review_note", "updated_at"])

    WorkflowTask.objects.filter(request_id=request.pk, task_class=TASK_CLASS,
                                status="pending").update(
        status="completed", completed_at=timezone.now(),
        completed_by_user_id=getattr(actor, "user_id", None), note=note[:300])
    notifications.enqueue(
        topic="leave.resumption.reviewed",
        dedupe_key=f"leave.resumption:{resumption.pk}:reviewed",
        recipient_user_id=request.user_id,
        subject="Your resumption has been reviewed",
        body=f"Resumption on {actual} recorded as {outcome.replace('_', ' ')}.",
        payload={"request_id": request.pk, "outcome": outcome})
    log.info("leave.resumption.reviewed request=%s outcome=%s", request.pk, outcome)
    return resumption


def _sync_early(*, request, actual) -> None:
    """Returned before the approved end date: record the real period and give
    back the days that were not taken (BR-EL-028)."""
    last_day = actual - timedelta(days=1)
    charged = counting.chargeable_days(category=request.category,
                                       start=request.period_from, end=last_day).days
    previously = request.days_counted
    if previously > charged:
        accounts.restore(user_id=request.user_id, category=request.category,
                         leave_year=request.period_from.year,
                         days=previously - charged, request_id=request.pk,
                         note="Early resumption — unused period restored")
    request.period_to = last_day
    request.days_counted = charged
    request.save(update_fields=["period_to", "days_counted", "updated_at"])
    _announce_sync(request, actual, "early")


def _sync_late(*, request, actual) -> None:
    """Returned after the approved end date: the extra days are charged."""
    last_day = actual - timedelta(days=1)
    charged = counting.chargeable_days(category=request.category,
                                       start=request.period_from, end=last_day).days
    additional = charged - request.days_counted
    if additional > 0:
        employee = facts.employee(request.user_id)
        policy = sel.current_policy(request.period_from.year)
        accounts.debit(user_id=request.user_id, category=request.category,
                       leave_year=request.period_from.year, days=additional,
                       request_id=request.pk,
                       entitled_days=accounts.entitlement_for(
                           request.category,
                           employee.kind if employee else cat.STAFF,
                           entitlements=policy.entitlements if policy else None),
                       note="Late resumption — additional period charged")
    request.period_to = last_day
    request.days_counted = charged
    request.save(update_fields=["period_to", "days_counted", "updated_at"])
    _announce_sync(request, actual, "late")


def _announce_sync(request, actual, kind: str) -> None:
    """The leave/attendance records must move with the account (BR-EL-028)."""
    notifications.enqueue(
        topic="leave.records.synchronise",
        dedupe_key=f"leave.records:{request.pk}:{kind}:{actual}",
        recipient_user_id=None,
        subject=f"Leave record synchronisation required — {request.reference}",
        body=(f"{kind.title()} resumption on {actual}: actual period "
              f"{request.period_from} to {request.period_to}, "
              f"{request.days_counted} day(s)."),
        payload={"request_id": request.pk, "actual_date": str(actual),
                 "period_to": str(request.period_to),
                 "days_counted": str(request.days_counted)})
