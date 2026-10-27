"""Atomic pending-request transitions."""

import logging

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.elm.domain.leave_requests import (
    ExistingLeaveRequest,
    LeaveRequestValidationError,
    ensure_no_overlap,
)
from modules.elm.models import (
    LeaveApprovalStep,
    LeaveRequest,
    LeaveWorkflowAction,
    SubstituteAssignment,
)
from modules.elm.services.routing import (
    ELMDependencyUnavailable,
    get_balance_provider,
    next_step_status,
)
from modules.elm.services.submission import _validate_nominee

log = logging.getLogger("fusion.elm")

_WITHDRAWABLE = frozenset(
    {
        LeaveRequest.Status.PENDING_SUBSTITUTE,
        LeaveRequest.Status.APPLICANT_ACTION_REQUIRED,
        LeaveRequest.Status.PENDING_UNIT_HEAD,
        LeaveRequest.Status.PENDING_ESTABLISHMENT,
        LeaveRequest.Status.PENDING_FINAL_DECISION,
        LeaveRequest.Status.PENDING_DIRECTOR_SANCTION,
    }
)

_ACTIONABLE = frozenset(
    {
        LeaveRequest.Status.PENDING_UNIT_HEAD,
        LeaveRequest.Status.PENDING_ESTABLISHMENT,
        LeaveRequest.Status.PENDING_FINAL_DECISION,
        LeaveRequest.Status.PENDING_DIRECTOR_SANCTION,
    }
)


def _advance_to_next_step(leave_request, completed_step):
    next_step = (
        leave_request.approval_steps.filter(
            status=LeaveApprovalStep.StepStatus.PENDING,
            sequence__gt=completed_step.sequence,
        )
        .order_by("sequence")
        .first()
    )
    if next_step is None:
        raise ELMDependencyUnavailable("The configured route has no next processing step.")
    leave_request.status = next_step_status(next_step.role_code)
    return leave_request.status


def _action_for(decision: str, role_code: str) -> str:
    if role_code == "UNIT_HEAD":
        if decision == "RECOMMENDED":
            return LeaveWorkflowAction.Action.UNIT_HEAD_RECOMMENDED
        if decision == "NOT_RECOMMENDED":
            return LeaveWorkflowAction.Action.UNIT_HEAD_NOT_RECOMMENDED
    if role_code == "ESTABLISHMENT" and decision == "PROCESSED":
        return LeaveWorkflowAction.Action.ESTABLISHMENT_PROCESSED
    if decision == "APPROVED":
        return LeaveWorkflowAction.Action.APPROVED
    if decision == "REJECTED":
        return LeaveWorkflowAction.Action.REJECTED
    raise BadRequestError("Decision is not valid for this workflow step.", code="invalid_decision")


def _check_current_overlap(leave_request):
    existing = [
        ExistingLeaveRequest(
            start_date=row.start_date,
            end_date=row.end_date,
            leave_type=row.leave_type,
            status=row.status,
            half_day=row.half_day,
        )
        for row in LeaveRequest.objects.filter(user_id=leave_request.user_id).exclude(
            pk=leave_request.pk
        )
    ]
    try:
        ensure_no_overlap(
            leave_type=leave_request.leave_type,
            start_date=leave_request.start_date,
            end_date=leave_request.end_date,
            half_day=leave_request.half_day,
            existing_requests=existing,
        )
    except LeaveRequestValidationError as exc:
        raise ConflictError(exc.message, code=exc.code) from exc


def _post_final_balance(leave_request):
    if leave_request.chargeable_days is None:
        raise ConflictError(
            "The request has no supported chargeable quantity.",
            code="unsupported_leave_counting_rule",
        )
    provider = get_balance_provider()
    post = getattr(provider, "approve_final_leave", None)
    if not callable(post):
        raise ELMDependencyUnavailable(
            "The configured balance integration lacks an atomic final-approval "
            "revalidation and posting operation."
        )
    try:
        accepted = post(
            request_id=leave_request.pk,
            user_id=leave_request.user_id,
            leave_type=leave_request.leave_type,
            chargeable_days=leave_request.chargeable_days,
            idempotency_key=f"elm:leave-request:{leave_request.pk}",
        )
    except Exception as exc:
        log.warning("elm.balance_post_failed error_type=%s", type(exc).__name__)
        raise ELMDependencyUnavailable(
            "The authoritative balance service could not approve and post this leave."
        ) from exc
    if accepted is not True:
        raise ConflictError(
            "The authoritative balance service refused final approval.",
            code="final_balance_revalidation_failed",
        )


def decide_leave_request(
    *, request_id: int, actor, decision: str, reason: str = ""
) -> LeaveRequest:
    """Record a review, recommendation, or final decision for the assigned actor."""
    with transaction.atomic():
        leave_request = LeaveRequest.objects.select_for_update().filter(pk=request_id).first()
        if leave_request is None:
            raise NotFoundError("No leave request was found.")
        if leave_request.status not in _ACTIONABLE:
            raise ConflictError(
                "This request is no longer pending workflow action.",
                code="request_not_actionable",
            )
        step = (
            leave_request.approval_steps.select_for_update()
            .filter(status=LeaveApprovalStep.StepStatus.PENDING)
            .order_by("sequence")
            .first()
        )
        if step is None:
            raise ConflictError("No pending approval step exists.", code="approval_step_missing")
        if step.assigned_user_id != actor.user_id:
            raise PermissionDeniedError("This action is not assigned to you.")
        if leave_request.status != next_step_status(step.role_code):
            raise ConflictError(
                "The request state does not match its pending approval step.",
                code="workflow_state_mismatch",
            )

        if step.role_code == "UNIT_HEAD":
            allowed = (
                {"APPROVED", "REJECTED"}
                if leave_request.leave_type in {"CL", "RH"}
                else {"RECOMMENDED", "NOT_RECOMMENDED"}
            )
        elif step.role_code == "ESTABLISHMENT":
            allowed = {"PROCESSED"}
        elif step.role_code in {"SANCTIONING_AUTHORITY", "DIRECTOR_SELF_SANCTION"}:
            allowed = {"APPROVED", "REJECTED"}
        else:
            raise ELMDependencyUnavailable("The pending workflow role is unsupported.")
        if decision not in allowed:
            raise BadRequestError(
                "Decision is not valid for the assigned workflow step.",
                code="invalid_decision",
            )
        if decision == "APPROVED":
            _check_current_overlap(leave_request)
            _post_final_balance(leave_request)

        previous_status = leave_request.status
        step.status = LeaveApprovalStep.StepStatus.COMPLETED
        step.decision = decision
        step.reason = reason
        step.completed_at = timezone.now()
        step.save(update_fields=["status", "decision", "reason", "completed_at"])

        if decision == "REJECTED":
            leave_request.status = LeaveRequest.Status.REJECTED
        elif decision == "APPROVED":
            leave_request.status = LeaveRequest.Status.APPROVED
        else:
            leave_request.status = _advance_to_next_step(leave_request, step)

        leave_request.save(update_fields=["status", "updated_at"])
        LeaveWorkflowAction.objects.create(
            request=leave_request,
            from_status=previous_status,
            to_status=leave_request.status,
            action=_action_for(decision, step.role_code),
            actor_user_id=actor.user_id,
            actor_role=actor.active_role or "",
            reason=reason,
        )
        return leave_request


def respond_to_substitute_assignment(
    *, request_id: int, actor, decision: str, reason: str = ""
) -> LeaveRequest:
    """Record the nominated employee's explicit acceptance or decline."""
    if decision not in {"ACCEPTED", "DECLINED"}:
        raise BadRequestError("decision must be ACCEPTED or DECLINED.", code="invalid_decision")
    with transaction.atomic():
        leave_request = LeaveRequest.objects.select_for_update().filter(pk=request_id).first()
        if leave_request is None:
            raise NotFoundError("No leave request was found.")
        if leave_request.status != LeaveRequest.Status.PENDING_SUBSTITUTE:
            raise ConflictError(
                "The request is not awaiting substitute response.",
                code="substitute_response_not_pending",
            )
        assignment = (
            leave_request.substitute_assignments.select_for_update()
            .filter(status=SubstituteAssignment.Status.PENDING)
            .order_by("-sequence")
            .first()
        )
        if assignment is None:
            raise ConflictError(
                "No pending substitute assignment exists.", code="substitute_assignment_missing"
            )
        if assignment.nominee_user_id != actor.user_id:
            raise PermissionDeniedError("This substitute response is not assigned to you.")

        previous_status = leave_request.status
        assignment.status = decision
        assignment.responded_at = timezone.now()
        assignment.save(update_fields=["status", "responded_at"])
        if decision == SubstituteAssignment.Status.ACCEPTED:
            first_step = (
                leave_request.approval_steps.filter(status=LeaveApprovalStep.StepStatus.PENDING)
                .order_by("sequence")
                .first()
            )
            if first_step is None:
                raise ELMDependencyUnavailable("No approval step follows substitute consent.")
            leave_request.status = next_step_status(first_step.role_code)
            action = LeaveWorkflowAction.Action.SUBSTITUTE_ACCEPTED
        else:
            leave_request.status = LeaveRequest.Status.APPLICANT_ACTION_REQUIRED
            action = LeaveWorkflowAction.Action.SUBSTITUTE_DECLINED

        leave_request.save(update_fields=["status", "updated_at"])
        LeaveWorkflowAction.objects.create(
            request=leave_request,
            from_status=previous_status,
            to_status=leave_request.status,
            action=action,
            actor_user_id=actor.user_id,
            actor_role=actor.active_role or "",
            reason=reason,
        )
        return leave_request


def nominate_replacement_substitute(
    *, request_id: int, actor, nominee_user_id: int
) -> LeaveRequest:
    """Record a replacement after the prior nominee declined."""
    with transaction.atomic():
        leave_request = (
            LeaveRequest.objects.select_for_update()
            .filter(pk=request_id, user_id=actor.user_id)
            .first()
        )
        if leave_request is None:
            raise NotFoundError("No leave request was found.")
        if leave_request.status != LeaveRequest.Status.APPLICANT_ACTION_REQUIRED:
            raise ConflictError(
                "A replacement substitute can be nominated only after a decline.",
                code="replacement_not_allowed",
            )
        previous = leave_request.substitute_assignments.order_by("-sequence").first()
        if (
            previous is None
            or previous.status != SubstituteAssignment.Status.DECLINED
            or previous.sequence != 1
        ):
            raise ConflictError(
                "No declined substitute assignment exists.",
                code="replacement_not_allowed",
            )
        _validate_nominee(
            actor=actor,
            nominee_user_id=nominee_user_id,
            leave_type=leave_request.leave_type,
            start_date=leave_request.start_date,
            end_date=leave_request.end_date,
            half_day=leave_request.half_day,
        )
        old_status = leave_request.status
        SubstituteAssignment.objects.create(
            request=leave_request,
            sequence=previous.sequence + 1,
            nominee_user_id=nominee_user_id,
        )
        leave_request.status = LeaveRequest.Status.PENDING_SUBSTITUTE
        leave_request.save(update_fields=["status", "updated_at"])
        LeaveWorkflowAction.objects.create(
            request=leave_request,
            from_status=old_status,
            to_status=leave_request.status,
            action=LeaveWorkflowAction.Action.SUBSTITUTE_NOMINATED,
            actor_user_id=actor.user_id,
            actor_role=actor.active_role or "",
        )
        return leave_request


def withdraw_leave_request(*, request_id: int, actor, reason: str = "") -> LeaveRequest:
    """Withdraw the caller's pending request and terminate its workflow."""
    with transaction.atomic():
        leave_request = (
            LeaveRequest.objects.select_for_update()
            .filter(pk=request_id, user_id=actor.user_id)
            .first()
        )
        if leave_request is None:
            raise NotFoundError("No leave request was found.")
        if leave_request.status not in _WITHDRAWABLE:
            raise ConflictError(
                "Only a pending request can be withdrawn.",
                code="request_not_withdrawable",
            )

        previous_status = leave_request.status
        leave_request.status = LeaveRequest.Status.WITHDRAWN
        leave_request.save(update_fields=["status", "updated_at"])
        LeaveWorkflowAction.objects.create(
            request=leave_request,
            from_status=previous_status,
            to_status=LeaveRequest.Status.WITHDRAWN,
            action=LeaveWorkflowAction.Action.WITHDRAWN,
            actor_user_id=actor.user_id,
            actor_role=actor.active_role or "",
            reason=reason,
        )
        return leave_request
