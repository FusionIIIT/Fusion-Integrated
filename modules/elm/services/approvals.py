"""Transactional approval and rejection workflow for leave requests."""

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError
from modules.elm.models import (
    LeaveApproval,
    LeaveAuditEvent,
    LeaveBalance,
    LeaveRequest,
)

STAGE_PERMISSION = {
    LeaveRequest.ApprovalStage.UNIT_HEAD: "elm.approve.unit_head",
    LeaveRequest.ApprovalStage.HIERARCHY: "elm.approve.hierarchy",
    LeaveRequest.ApprovalStage.DIRECTOR: "elm.approve.director",
}


@transaction.atomic
def decide_leave_request(
    *,
    request_id: int,
    actor_id: int,
    decision: str,
    comments: str = "",
    permissions=(),
) -> LeaveRequest:
    """Approve the current stage or reject a pending leave request."""
    if decision not in {
        LeaveApproval.Decision.APPROVED,
        LeaveApproval.Decision.NOT_RECOMMENDED,
        LeaveApproval.Decision.REJECTED,
    }:
        raise ConflictError("Invalid decision.", code="invalid_decision")

    leave = LeaveRequest.objects.select_for_update().filter(
        pk=request_id
    ).first()

    if leave is None:
        raise ConflictError("Leave request not found.", code="not_found")

    if leave.status != LeaveRequest.Status.PENDING:
        raise ConflictError(
            "This leave request is no longer pending.",
            code="request_not_pending",
        )

    required_permission = STAGE_PERMISSION.get(leave.approval_stage)
    if not required_permission or required_permission not in permissions:
        raise ConflictError(
            "You are not authorized to decide this approval stage.",
            code="approval_forbidden",
        )

    if actor_id == leave.employee_id:
        raise ConflictError(
            "Applicants cannot approve their own leave.",
            code="self_approval",
        )

    if decision == LeaveApproval.Decision.NOT_RECOMMENDED and (
        leave.approval_stage != LeaveRequest.ApprovalStage.UNIT_HEAD
        or leave.leave_category in {"CL", "RH"}
    ):
        raise ConflictError(
            "Not Recommended is only valid for the Unit Head stage "
            "of SCL, EL, COL, or VL requests.",
            code="invalid_recommendation",
        )

    if (
        decision == LeaveApproval.Decision.REJECTED
        and leave.approval_stage == LeaveRequest.ApprovalStage.UNIT_HEAD
        and leave.leave_category not in {"CL", "RH"}
    ):
        raise ConflictError(
            "The Unit Head must recommend or not recommend this request; "
            "final rejection belongs to the higher approval path.",
            code="unit_head_cannot_finally_reject",
        )

    now = timezone.now()

    approval, created = LeaveApproval.objects.get_or_create(
        leave_request=leave,
        stage=leave.approval_stage,
        defaults={"approver_id": actor_id},
    )

    if not created and approval.decision != LeaveApproval.Decision.PENDING:
        raise ConflictError(
            "This approval stage has already been decided.",
            code="stage_already_decided",
        )

    approval.approver_id = actor_id
    approval.decision = decision
    approval.comments = comments.strip()
    approval.decided_at = now
    approval.save()

    previous_stage = leave.approval_stage

    unit_head_final = (
        previous_stage == LeaveRequest.ApprovalStage.UNIT_HEAD
        and leave.leave_category in {"CL", "RH"}
    )

    if decision == LeaveApproval.Decision.REJECTED:
        leave.status = LeaveRequest.Status.REJECTED
        leave.approval_stage = LeaveRequest.ApprovalStage.COMPLETED
        leave.final_approver_id = actor_id
        leave.final_approved_at = now
    elif previous_stage == LeaveRequest.ApprovalStage.UNIT_HEAD and not unit_head_final:
        leave.approval_stage = LeaveRequest.ApprovalStage.HIERARCHY
    elif previous_stage == LeaveRequest.ApprovalStage.HIERARCHY:
        leave.approval_stage = LeaveRequest.ApprovalStage.DIRECTOR
    else:
        leave.approval_stage = LeaveRequest.ApprovalStage.COMPLETED
        leave.status = LeaveRequest.Status.APPROVED
        leave.final_approver_id = actor_id
        leave.final_approved_at = now

        if leave.leave_category in {"EL", "COL", "VL"}:
            balance = LeaveBalance.objects.select_for_update().filter(
                employee_id=leave.employee_id,
                leave_category=leave.leave_category,
                year=leave.start_date.year,
            ).first()

            if balance is None:
                raise ConflictError(
                    "Leave balance is not configured.",
                    code="balance_missing",
                )

            from modules.elm.domain.leave_rules import count_leave_days

            days = count_leave_days(
                leave.start_date, leave.end_date, leave.leave_category
            )

            if balance.available_days < days:
                raise ConflictError(
                    "Insufficient leave balance at final approval.",
                    code="insufficient_balance",
                )

            balance.used_days += days
            balance.save(update_fields=["used_days", "updated_at"])

    leave.save()

    LeaveAuditEvent.objects.create(
        leave_request=leave,
        actor_id=actor_id,
        action=f"{decision}_{previous_stage}",
        details={
            "decision": decision,
            "stage": previous_stage,
            "next_stage": leave.approval_stage,
            "comments": comments.strip(),
        },
    )

    return leave
