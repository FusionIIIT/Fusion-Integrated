"""Cancellation, extension and resumption (CW-EL-02..04).

Each of these is its own aggregate with its own states, so the parent leave's
approved record stays readable and the change to it is traceable. Approval
posts only what actually changed: an extension posts its increment, a
cancellation returns the days it took back.
"""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError
from modules.leave.services.errors import ValidationError
from modules.leave.domain import categories as cat
from modules.leave.domain import counting, routing, state_machine as sm
from modules.leave.models import (
    CREDIT,
    DEBIT,
    ApprovalTask,
    CancellationRequest,
    ExtensionRequest,
    LeaveRequest,
    ResumptionRequest,
)
from modules.leave.models.requests import (
    KIND_CANCELLATION_ESTABLISHMENT,
    KIND_CANCELLATION_FINAL,
    KIND_CANCELLATION_UNIT_HEAD,
    KIND_EXTENSION_ESTABLISHMENT,
    KIND_EXTENSION_FINAL,
    KIND_EXTENSION_UNIT_HEAD,
    KIND_RESUMPTION_REVIEW,
)
from modules.leave.services import authz, calendar, ledger, notifications, policy
from modules.leave.services import tasks as task_service

log = logging.getLogger("fusion.leave")


def _require_approved(request_obj: LeaveRequest, *, starting: bool = False) -> None:
    """BR-EL-023/025/027: these act on approved leave. A cancellation is only
    possible before the leave starts, which is what makes it a reversal rather
    than a refund."""
    if request_obj.status != sm.APPROVED:
        raise ConflictError(
            f"Request #{request_obj.pk} is {request_obj.status}; this action "
            "applies to approved leave.")
    if starting and request_obj.start_date <= date.today():
        raise ConflictError(
            "This leave has already started. Ask the Sanctioning Authority to "
            "review an early return instead.")


@transaction.atomic
def request_cancellation(actor, request_obj: LeaveRequest, reason: str
                         ) -> CancellationRequest:
    """BR-EL-023: the employee withdraws approved leave before it starts, and it
    goes through the same hierarchy as the original."""
    authz.require(actor, authz.P_CREATE)
    authz.require_owner(actor, request_obj)
    _require_approved(request_obj, starting=True)
    if not reason.strip():
        raise ValidationError("Give a reason for cancelling this leave.")

    existing = CancellationRequest.objects.filter(
        leave_request=request_obj, status__in=sm.CANCELLATION_PENDING).first()
    if existing is not None:
        raise ConflictError("A cancellation is already in progress for this leave.")

    cancellation = CancellationRequest.objects.create(
        leave_request=request_obj, reason=reason.strip(),
        status=sm.CANCEL_PENDING_UNIT_HEAD)
    unit = request_obj.org_unit
    _assign_next(subject=sm.CANCELLATION, obj=cancellation, leave_request=request_obj,
                 status=cancellation.status, unit=unit)
    notifications.enqueue(
        topic="leave.cancellation.requested",
        dedupe_key=f"cancel-requested:{cancellation.pk}",
        recipient_user_id=unit.head_user_id if unit is not None else None,
        subject="Leave cancellation to review",
        body=f"Request #{request_obj.pk} was cancelled by the employee.")
    return cancellation


@transaction.atomic
def decide_cancellation(actor, task: ApprovalTask, *, approve: bool, note: str = "",
                        recommendation: str = "", now=None) -> CancellationRequest:
    authz.require(actor, authz.P_APPROVE)
    authz.require_assignee(actor, task)
    authz.require_pending(task)
    cancellation = task_to_cancellation(task)
    now = now or timezone.now()
    leave_request = cancellation.leave_request

    if task.kind == KIND_CANCELLATION_UNIT_HEAD:
        target = _unit_head_cancellation_step(
            cancellation, task, approve=approve, note=note,
            recommendation=recommendation, now=now)
    elif task.kind == KIND_CANCELLATION_ESTABLISHMENT:
        target = sm.CANCEL_PENDING_FINAL
    elif task.kind == KIND_CANCELLATION_FINAL:
        target = sm.CANCEL_APPROVED if approve else sm.CANCEL_REJECTED
    else:
        raise ConflictError(f"Task kind {task.kind} is not a cancellation step.")

    if not sm.is_legal(sm.CANCELLATION, cancellation.status, target):
        raise ConflictError(
            f"A cancellation that is {cancellation.status} cannot move to {target}.")

    task_service.complete_task(task, outcome=target, note=note, now=now)
    cancellation.status = target
    cancellation.decided_by_user_id = authz.own_id(actor)
    cancellation.decided_at = now
    cancellation.decision_note = note[:500]
    cancellation.save()

    if target == sm.CANCEL_APPROVED:
        # The days go back, and the leave itself is cancelled.
        ledger.post([ledger.Posting(
            user_id=leave_request.user_id, year=leave_request.start_date.year,
            category=leave_request.category, kind=CREDIT,
            days=Decimal(leave_request.requested_days),
            note=f"Cancelled leave request #{leave_request.pk}",
            leave_request_id=leave_request.pk)],
            created_by_user_id=authz.own_id(actor))
        leave_request.status = sm.CANCELLED
        leave_request.save(update_fields=["status", "updated_at"])
        task_service.cancel_open_tasks(subject_type=sm.CANCELLATION,
                                       subject_id=cancellation.pk)
    elif target in sm.CANCELLATION_PENDING:
        # The Unit Head is not the last word on higher-sanction leave, so the next
        # authority needs its own task or the cancellation stops here.
        _assign_next(subject=sm.CANCELLATION, obj=cancellation,
                     leave_request=leave_request, status=target, unit=leave_request.org_unit)
    else:
        task_service.cancel_open_tasks(subject_type=sm.CANCELLATION,
                                       subject_id=cancellation.pk)

    notifications.enqueue(
        topic="leave.cancellation.decided",
        dedupe_key=f"cancel-decided:{cancellation.pk}:{target}",
        recipient_user_id=leave_request.user_id,
        subject="Leave cancellation approved" if approve else "Leave cancellation rejected",
        body=f"Your cancellation of request #{leave_request.pk} was "
             f"{'approved' if approve else 'rejected'}.")
    return cancellation


def _unit_head_cancellation_step(cancellation, task, *, approve: bool, note: str,
                                 recommendation: str, now) -> str:
    """The same split as a new request: CL/RH finish with the Unit Head, the rest
    continue up (BR-EL-023 mirrors BR-EL-016). The task itself is completed by the
    caller, once, whatever the step turns out to be."""
    cancellation.unit_head_recommendation = recommendation or (
        "recommended" if approve else "not_recommended")
    cancellation.save(update_fields=["unit_head_recommendation", "updated_at"])
    if routing.is_unit_head_final(cancellation.leave_request.category):
        return sm.CANCEL_APPROVED if approve else sm.CANCEL_REJECTED
    return routing.after_unit_head_cancellation(
        category=cancellation.leave_request.category,
        establishment_configured=policy.current_policy().establishment_step_enabled)


@transaction.atomic
def withdraw_cancellation(actor, cancellation: CancellationRequest) -> CancellationRequest:
    authz.require(actor, authz.P_CREATE)
    authz.require_owner(actor, cancellation.leave_request)
    if cancellation.status not in sm.CANCELLATION_PENDING:
        raise ConflictError("This cancellation has already been decided.")
    task_service.cancel_open_tasks(subject_type=sm.CANCELLATION,
                                   subject_id=cancellation.pk)
    cancellation.status = sm.CANCEL_WITHDRAWN
    cancellation.save(update_fields=["status", "updated_at"])
    return cancellation


@transaction.atomic
def request_extension(actor, request_obj: LeaveRequest, *, additional_start: date,
                      additional_end: date, reason: str) -> ExtensionRequest:
    """BR-EL-025: extra time on leave already under way or about to start."""
    authz.require(actor, authz.P_CREATE)
    authz.require_owner(actor, request_obj)
    _require_approved(request_obj)
    if request_obj.category not in routing.ONGOING_CATEGORIES:
        raise ValidationError(
            f"{request_obj.category} leave cannot be extended; only Earned, "
            "Commuted and Vacation Leave can.")
    if additional_start > additional_end:
        raise ValidationError("The last date cannot be before the first date.")
    if additional_end < request_obj.end_date:
        raise ValidationError("An extension must add time after the existing end date.")
    if not reason.strip():
        raise ValidationError("Give a reason for the extension.")

    substitution_required = policy.substitute_required(request_obj.category)
    extension = ExtensionRequest.objects.create(
        leave_request=request_obj, additional_start_date=additional_start,
        additional_end_date=additional_end, additional_days=_extension_days(
            request_obj, additional_start, additional_end),
        reason=reason.strip(),
        substitute_required=substitution_required,
        # CW-EL-03 STT rows 1-2: an extension that needs a substitute waits for
        # one before the hierarchy sees it, exactly as a new request does.
        status=sm.EXT_AWAITING_SUBSTITUTE if substitution_required
        else sm.EXT_AWAITING_UNIT_HEAD)
    unit = request_obj.org_unit
    _assign_next(subject=sm.EXTENSION, obj=extension, leave_request=request_obj,
                 status=extension.status, unit=unit)
    notifications.enqueue(
        topic="leave.extension.requested",
        dedupe_key=f"extend-requested:{extension.pk}",
        recipient_user_id=unit.head_user_id if unit is not None else None,
        subject="Leave extension to review",
        body=f"Request #{request_obj.pk} was extended by the employee.")
    return extension


def _extension_days(request_obj: LeaveRequest, start: date, end: date) -> Decimal:
    excluded: set[date] = set()
    if request_obj.category in cat.CONTINUOUS:
        excluded = calendar.closed_holiday_dates(start, end)
    count = counting.count_days(request_obj.category, start, end,
                                excluded_holidays=excluded)
    if count == 0:
        raise ValidationError(
            "That range contains no countable leave days once weekends and "
            "holidays are removed.")
    return Decimal(count)


@transaction.atomic
def decide_extension(actor, task: ApprovalTask, *, approve: bool, note: str = "",
                     recommendation: str = "", now=None) -> ExtensionRequest:
    authz.require(actor, authz.P_APPROVE)
    authz.require_assignee(actor, task)
    authz.require_pending(task)
    extension = task_to_extension(task)
    now = now or timezone.now()
    leave_request = extension.leave_request

    if task.kind == KIND_EXTENSION_UNIT_HEAD:
        target = _unit_head_extension_step(
            extension, task, approve=approve, note=note,
            recommendation=recommendation, now=now)
    elif task.kind == KIND_EXTENSION_ESTABLISHMENT:
        target = sm.EXT_PENDING_FINAL
    elif task.kind == KIND_EXTENSION_FINAL:
        target = sm.EXT_APPROVED if approve else sm.EXT_REJECTED
    else:
        raise ConflictError(f"Task kind {task.kind} is not an extension step.")

    if not sm.is_legal(sm.EXTENSION, extension.status, target):
        raise ConflictError(
            f"An extension that is {extension.status} cannot move to {target}.")

    task_service.complete_task(task, outcome=target, note=note, now=now)
    extension.status = target
    extension.decided_by_user_id = authz.own_id(actor)
    extension.decided_at = now
    extension.decision_note = note[:500]
    extension.save()

    if target == sm.EXT_APPROVED:
        # Only the increment is debited; the base was already charged (BR-EL-025).
        ledger.post([ledger.Posting(
            user_id=leave_request.user_id, year=additional_year(extension),
            category=leave_request.category, kind=DEBIT,
            days=extension.additional_days,
            note=f"Approved extension #{extension.pk} of request "
                 f"#{leave_request.pk}",
            leave_request_id=leave_request.pk)],
            created_by_user_id=authz.own_id(actor))
        task_service.cancel_open_tasks(subject_type=sm.EXTENSION,
                                       subject_id=extension.pk)
    elif target in sm.EXTENSION_PENDING:
        # Higher-sanction leave continues up the hierarchy, and the next authority
        # gets its own task.
        _assign_next(subject=sm.EXTENSION, obj=extension,
                     leave_request=leave_request, status=target, unit=leave_request.org_unit)
    else:
        task_service.cancel_open_tasks(subject_type=sm.EXTENSION,
                                       subject_id=extension.pk)

    notifications.enqueue(
        topic="leave.extension.decided",
        dedupe_key=f"extend-decided:{extension.pk}:{target}",
        recipient_user_id=leave_request.user_id,
        subject="Leave extension approved" if approve else "Leave extension rejected",
        body=f"Your extension to request #{leave_request.pk} was "
             f"{'approved' if approve else 'rejected'}.")
    return extension


def _unit_head_extension_step(extension, task, *, approve: bool, note: str,
                              recommendation: str, now) -> str:
    extension.unit_head_recommendation = recommendation or (
        "recommended" if approve else "not_recommended")
    extension.save(update_fields=["unit_head_recommendation", "updated_at"])
    return routing.after_unit_head(
        category=extension.leave_request.category,
        establishment_configured=policy.current_policy().establishment_step_enabled)


def additional_year(extension: ExtensionRequest) -> int:
    """The year the extra days fall in, which may not be the leave's own year
    when a request straddles New Year."""
    return extension.additional_start_date.year


# -- extension substitution -----------------------------------------------------

def nomination_created(extension: ExtensionRequest) -> None:
    """An applicant nominated somebody for this extension, so it is waiting on
    the answer rather than sitting in applicant_action_required (STT row 4)."""
    if extension.status == sm.EXT_APPLICANT_ACTION_REQUIRED:
        if not sm.is_legal(sm.EXTENSION, extension.status, sm.EXT_AWAITING_SUBSTITUTE):
            raise ConflictError(
                f"An extension that is {extension.status} cannot take a substitute "
                "nomination any more.")
        extension.status = sm.EXT_AWAITING_SUBSTITUTE
        extension.save(update_fields=["status", "updated_at"])


def substitute_accepted(nomination, *, now=None) -> None:
    """A substitute accepted cover for the extension, so it joins the hierarchy
    (CW-EL-03 STT row 2)."""
    extension = _extension_of(nomination)
    now = now or timezone.now()
    if not sm.is_legal(sm.EXTENSION, extension.status, sm.EXT_AWAITING_UNIT_HEAD):
        raise ConflictError(
            f"An extension that is {extension.status} cannot move to the Unit "
            "Head review.")
    extension.status = sm.EXT_AWAITING_UNIT_HEAD
    extension.save(update_fields=["status", "updated_at"])
    _assign_next(subject=sm.EXTENSION, obj=extension,
                 leave_request=extension.leave_request, status=extension.status,
                 unit=extension.leave_request.org_unit)
    del now


def substitute_declined(nomination) -> None:
    """BR-EL-014 as it applies to an extension: the employee nominates somebody
    else, and nothing reaches the Unit Head yet."""
    extension = _extension_of(nomination)
    if not sm.is_legal(sm.EXTENSION, extension.status,
                       sm.EXT_APPLICANT_ACTION_REQUIRED):
        raise ConflictError(
            f"An extension that is {extension.status} cannot be sent back to the "
            "applicant.")
    extension.status = sm.EXT_APPLICANT_ACTION_REQUIRED
    extension.save(update_fields=["status", "updated_at"])


def _extension_of(nomination):
    extension = ExtensionRequest.objects.filter(
        pk=nomination.extension_request_id).first()
    if extension is None or extension.leave_request_id != nomination.leave_request_id:
        raise ConflictError(
            f"Nomination #{nomination.pk} does not point at an existing extension.")
    return extension


@transaction.atomic
def withdraw_extension(actor, extension: ExtensionRequest) -> ExtensionRequest:
    authz.require(actor, authz.P_CREATE)
    authz.require_owner(actor, extension.leave_request)
    if extension.status not in sm.EXTENSION_PENDING:
        raise ConflictError("This extension has already been decided.")
    task_service.cancel_open_tasks(subject_type=sm.EXTENSION, subject_id=extension.pk)
    extension.status = sm.EXT_WITHDRAWN
    extension.save(update_fields=["status", "updated_at"])
    return extension


@transaction.atomic
def submit_resumption(actor, request_obj: LeaveRequest, *, actual_resumption_date: date,
                      details: str = "") -> ResumptionRequest:
    """BR-EL-027: the employee reports actually returning. The Sanctioning
    Authority reviews it; there is no automatic closure (BR-EL-028)."""
    authz.require(actor, authz.P_CREATE)
    authz.require_owner(actor, request_obj)
    _require_approved(request_obj)
    if request_obj.category not in routing.ONGOING_CATEGORIES:
        raise ValidationError(
            "Only Earned, Commuted and Vacation Leave have a resumption step.")
    if actual_resumption_date > date.today():
        raise ValidationError("A resumption date cannot be in the future.")

    resumption = ResumptionRequest.objects.create(
        leave_request=request_obj, actual_resumption_date=actual_resumption_date,
        details=details.strip(), status=sm.RESUMPTION_PENDING)
    _assign_next(subject=sm.RESUMPTION, obj=resumption, leave_request=request_obj,
                 status=resumption.status, unit=request_obj.org_unit)
    notifications.enqueue(
        topic="leave.resumption.submitted",
        dedupe_key=f"resumption:{resumption.pk}",
        recipient_user_id=request_obj.user_id,
        subject="Resumption submitted",
        body=f"You reported returning on {actual_resumption_date}.")
    return resumption


@transaction.atomic
def review_resumption(actor, task: ApprovalTask, *, note: str = "",
                      now=None) -> ResumptionRequest:
    """The review outcome follows the date, not a choice by the reviewer:
    on time, early or late (CW-EL-04 STT rows 2-4)."""
    authz.require(actor, authz.P_APPROVE)
    authz.require_assignee(actor, task)
    authz.require_pending(task)
    resumption = task_to_resumption(task)
    now = now or timezone.now()
    leave_request = resumption.leave_request

    actual = resumption.actual_resumption_date
    approved_end = leave_request.end_date
    if actual < approved_end:
        target, delta = sm.RESUMPTION_EARLY, (Decimal(actual - approved_end).days)
    elif actual > approved_end:
        target, delta = sm.RESUMPTION_LATE, (Decimal(actual - approved_end).days)
    else:
        target, delta = sm.RESUMPTION_NO_ADJUSTMENT, Decimal("0")

    if not sm.is_legal(sm.RESUMPTION, resumption.status, target):
        raise ConflictError(f"A resumption that is {resumption.status} cannot "
                            f"move to {target}.")

    task_service.complete_task(task, outcome=target, note=note, now=now)
    resumption.status = target
    resumption.reviewed_by_user_id = authz.own_id(actor)
    resumption.reviewed_at = now
    resumption.review_note = note[:500]
    resumption.adjustment_days = delta
    resumption.save()

    # Early return owes the unused days back; a late return owes the extra ones.
    if delta:
        ledger.post([ledger.Posting(
            user_id=leave_request.user_id, year=approved_end.year,
            category=leave_request.category,
            kind=DEBIT if delta > 0 else CREDIT,
            days=abs(delta),
            note=f"Resumption review #{resumption.pk} of request "
                 f"#{leave_request.pk}",
            leave_request_id=leave_request.pk)],
            created_by_user_id=authz.own_id(actor))

    notifications.enqueue(
        topic="leave.resumption.reviewed",
        dedupe_key=f"resumption-reviewed:{resumption.pk}",
        recipient_user_id=leave_request.user_id,
        subject="Resumption reviewed",
        body=f"Your return on {actual} was recorded as {target.replace('_', ' ')}.")
    return resumption


# -- shared plumbing ----------------------------------------------------------

CANCELLATION_TASKS = {KIND_CANCELLATION_UNIT_HEAD: sm.CANCEL_PENDING_UNIT_HEAD,
                      KIND_CANCELLATION_ESTABLISHMENT: sm.CANCEL_PENDING_ESTABLISHMENT,
                      KIND_CANCELLATION_FINAL: sm.CANCEL_PENDING_FINAL}
EXTENSION_TASKS = {KIND_EXTENSION_UNIT_HEAD: sm.EXT_AWAITING_UNIT_HEAD,
                   KIND_EXTENSION_ESTABLISHMENT: sm.EXT_PENDING_ESTABLISHMENT,
                   KIND_EXTENSION_FINAL: sm.EXT_PENDING_FINAL}
RESUMPTION_TASKS = {KIND_RESUMPTION_REVIEW: sm.RESUMPTION_PENDING}


def _assign_next(*, subject: str, obj, leave_request: LeaveRequest, status: str,
                 unit) -> None:
    kind = {sm.CANCEL_PENDING_UNIT_HEAD: KIND_CANCELLATION_UNIT_HEAD,
            sm.CANCEL_PENDING_ESTABLISHMENT: KIND_CANCELLATION_ESTABLISHMENT,
            sm.CANCEL_PENDING_FINAL: KIND_CANCELLATION_FINAL,
            sm.EXT_AWAITING_UNIT_HEAD: KIND_EXTENSION_UNIT_HEAD,
            sm.EXT_PENDING_ESTABLISHMENT: KIND_EXTENSION_ESTABLISHMENT,
            sm.EXT_PENDING_FINAL: KIND_EXTENSION_FINAL,
            sm.RESUMPTION_PENDING: KIND_RESUMPTION_REVIEW}.get(status)
    if kind is None:
        return
    assignee = _lifecycle_assignee(leave_request, status)
    if assignee is None:
        raise ValidationError(
            f"No authority is configured to handle this {subject} request. Ask "
            "the Leave Administrator to configure the routing.")
    task_service.open_task(leave_request=leave_request, subject_type=subject,
                           subject_id=obj.pk, kind=kind,
                           assignee_user_id=assignee)


def _lifecycle_assignee(leave_request: LeaveRequest, status: str) -> int | None:
    step_kind = {sm.CANCEL_PENDING_UNIT_HEAD: routing.UNIT_HEAD_STEP,
                 sm.EXT_AWAITING_UNIT_HEAD: routing.UNIT_HEAD_STEP,
                 sm.RESUMPTION_PENDING: routing.FINAL_SANCTION_STEP,
                 }.get(status)
    if status in (sm.CANCEL_PENDING_ESTABLISHMENT, sm.EXT_PENDING_ESTABLISHMENT):
        step_kind = routing.ESTABLISHMENT_STEP
    if status in (sm.CANCEL_PENDING_FINAL, sm.EXT_PENDING_FINAL):
        step_kind = routing.FINAL_SANCTION_STEP

    unit = leave_request.org_unit
    if step_kind == routing.UNIT_HEAD_STEP:
        return unit.head_user_id if unit is not None else None

    step = policy.resolved_route(leave_request.category, org_unit=unit).step(step_kind)
    if step is not None and step.assigned:
        return step.user_id
    return unit.head_user_id if unit is not None else None


def task_to_cancellation(task: ApprovalTask) -> CancellationRequest:
    return _one(CancellationRequest, task)


def task_to_extension(task: ApprovalTask) -> ExtensionRequest:
    return _one(ExtensionRequest, task)


def task_to_resumption(task: ApprovalTask) -> ResumptionRequest:
    return _one(ResumptionRequest, task)


def _one(model, task: ApprovalTask):
    row = model.objects.filter(pk=task.subject_id).first()
    if row is None or row.leave_request_id != task.leave_request_id:
        raise ConflictError(
            f"Task #{task.pk} does not point at an existing {model.__name__}.")
    return row


#: Task kinds that are not leave decisions, so the one deciding endpoint can
#: refuse them with a pointer instead of an error the caller has to decode.
NON_DECISION_KINDS: frozenset[str] = frozenset({
    KIND_CANCELLATION_UNIT_HEAD, KIND_CANCELLATION_ESTABLISHMENT,
    KIND_CANCELLATION_FINAL, KIND_EXTENSION_UNIT_HEAD,
    KIND_EXTENSION_ESTABLISHMENT, KIND_EXTENSION_FINAL, KIND_RESUMPTION_REVIEW,
})
