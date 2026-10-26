"""Resumption of duty and its review (EL-UC-010, EL-UC-011, CW-EL-04)."""
from __future__ import annotations

from datetime import date

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.leave.domain import resumption as rd
from modules.leave.domain import routing, sla
from modules.leave.domain import state_machine as sm
from modules.leave.models import LeaveRequest, RequestEvent, Resumption, Task
from modules.leave.services import accounts, authz, notifications, workflow


def reviewer_for(leave: LeaveRequest) -> str:
    """BR-EL-027: the applicable Sanctioning Authority, the Director for the Director's own."""
    if leave.is_director_applicant:
        return routing.DIRECTOR_DESIGNATION
    return workflow.designation_for(leave, sm.AUTHORITY)


@transaction.atomic
def submit(*, actor, leave_id: int, resumption_date: date, details: str = "") -> Resumption:
    authz.require(actor, "leave.request.create")
    leave = workflow.lock_request(leave_id, LeaveRequest.objects.filter(
        user_id=actor.user_id, kind=sm.NEW))
    if leave.status != sm.APPROVED:
        raise ConflictError("Resumption is submitted for an approved leave.",
                            code="not_approved")
    if Resumption.objects.filter(leave=leave).exists():
        raise ConflictError("You have already submitted your resumption for this leave.",
                            code="already_resumed")
    if LeaveRequest.objects.filter(parent=leave, kind=sm.EXTENSION,
                                   status__in=sm.PENDING).exists():
        raise ConflictError("An extension of this leave is still pending. Withdraw it or wait "
                            "for its decision before resuming.", code="extension_pending")
    try:
        rd.check_submission(category=leave.category, leave_start=leave.start_date,
                            resumption_date=resumption_date, today=workflow.today())
    except rd.ResumptionRefused as exc:
        raise ConflictError(str(exc), code=exc.code) from exc
    designation = reviewer_for(leave)
    res = Resumption.objects.create(leave=leave, resumption_date=resumption_date,
                                    details=details[:500], status=rd.move(rd.DRAFT, "submit"),
                                    reviewer_designation=designation)
    task = Task.objects.create(request=leave, step=sla.RESUMPTION_REVIEW,
                               assignee_designation=designation)
    RequestEvent.objects.create(request=leave, event="resumption_submitted",
                                from_status=leave.status, to_status=leave.status,
                                actor_user_id=actor.user_id, actor_role=authz.acting_role(actor),
                                remarks=f"Resumed {resumption_date}")
    notifications.enqueue(
        topic="task.assigned", dedupe_key=f"task:{task.pk}", designation=designation,
        subject=f"Resumption for leave #{leave.pk} awaits review",
        body=f"An employee resumed duty on {resumption_date} after {leave.category} "
             f"leave #{leave.pk}. Review it in your Leave approvals queue.")
    return res


@transaction.atomic
def review(*, task_id: int, actor, remarks: str = "") -> Resumption:
    """BR-EL-028: the balance moves only here, after review, and never below zero."""
    authz.require(actor, "leave.resumption.review")
    task = Task.objects.filter(pk=task_id, step=sla.RESUMPTION_REVIEW).first()
    if task is None:
        raise NotFoundError("No such task in your queue.")
    leave = workflow.lock_request(task.request_id)
    task = Task.objects.select_for_update().get(pk=task.pk)
    role, own = authz.acting_role(actor), leave.user_id == actor.user_id
    if task.assignee_designation != role:
        raise NotFoundError("No such task in your queue.")
    if own and not (leave.is_director_applicant and role == routing.DIRECTOR_DESIGNATION):
        raise PermissionDeniedError("You cannot review your own resumption.", code="own_request")
    if task.status != Task.OPEN:
        raise ConflictError("This resumption has already been reviewed.", code="task_closed")
    res = Resumption.objects.select_for_update().get(leave=leave)
    approved_end = workflow.effective_end(leave)
    out = rd.classify(approved_end=approved_end, resumption_date=res.resumption_date)
    accounts.lock(leave.user_id)
    if out.kind == rd.LATE:
        held = accounts.balances([leave.user_id], leave.leave_year)[leave.user_id][leave.category]
        if held < -out.adjustment:
            raise ConflictError(
                f"The late return needs {-out.adjustment} more day(s) of {leave.category} and "
                f"{held} remain. Regularise the excess (another leave, or an administrative "
                f"record) before completing this review.", code="insufficient_balance")
    if out.adjustment:
        accounts.post(user_id=leave.user_id, year=leave.leave_year, category=leave.category,
                      delta=out.adjustment,
                      entry_type="reversal" if out.adjustment > 0 else "debit",
                      key=f"resumption:{res.pk}", request=leave,
                      note=f"{out.kind.title()} resumption on {res.resumption_date}",
                      actor_id=actor.user_id)
    res.status = rd.move(res.status, out.kind)
    res.outcome, res.actual_end_date, res.adjustment_days = out.kind, out.actual_end, out.adjustment
    res.reviewed_by_user_id, res.reviewed_at = actor.user_id, timezone.now()
    res.review_remarks = remarks[:500]
    res.save()
    task.status, task.closed_at, task.closed_by_user_id = Task.DONE, timezone.now(), actor.user_id
    task.save(update_fields=["status", "closed_at", "closed_by_user_id"])
    RequestEvent.objects.create(request=leave, event="resumption_reviewed",
                                from_status=leave.status, to_status=leave.status,
                                actor_user_id=actor.user_id, actor_role=role, outcome=out.kind,
                                remarks=remarks[:500])
    notifications.enqueue(
        topic="decision.final", dedupe_key=f"resumption:{res.pk}", user_id=leave.user_id,
        subject=f"Your resumption from leave #{leave.pk} was reviewed",
        body=f"Your resumption on {res.resumption_date} was reviewed as {out.kind}."
             + (f" Balance adjusted by {out.adjustment} day(s)." if out.adjustment else ""))
    return res
