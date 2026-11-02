"""Workflow services for approvals, substitute responses, and sanction decisions."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from modules.elm.domain.entities import LeaveStatus
from modules.elm.domain.errors import InvalidLeaveTransitionError
from modules.elm.domain.state_machine import LeaveStateMachine
from modules.elm.models.leaves import LeaveRequest, LeaveTransitionHistory
from modules.elm.services.balances import deduct_balance


def respond_as_substitute(
    *,
    leave_id: int,
    substitute_user_id: int,
    accepted: bool,
    remarks: str = "",
) -> LeaveRequest:
    """Record designated substitute's decision to accept or decline coverage."""
    with transaction.atomic():
        req = LeaveRequest.objects.select_for_update().get(pk=leave_id)
        current = LeaveStatus(req.status)
        result = LeaveStateMachine.process_substitute_response(current, accepted=accepted)
        if not result.is_valid:
            raise InvalidLeaveTransitionError(result.message)

        prev_status = req.status
        req.status = result.next_status.value
        req.substitute_status = "accepted" if accepted else "declined"
        req.substitute_remarks = remarks
        req.save(update_fields=["status", "substitute_status", "substitute_remarks", "updated_at"])

        LeaveTransitionHistory.objects.create(
            leave_request=req,
            from_status=prev_status,
            to_status=result.next_status.value,
            actor_user_id=substitute_user_id,
            remarks=f"Substitute {'accepted' if accepted else 'declined'} responsibility. {remarks}".strip(),
        )
        return req


def review_as_unit_head(
    *,
    leave_id: int,
    unit_head_user_id: int,
    recommended: bool,
    remarks: str = "",
) -> LeaveRequest:
    """Record Unit Head's recommendation or rejection."""
    with transaction.atomic():
        req = LeaveRequest.objects.select_for_update().get(pk=leave_id)
        current = LeaveStatus(req.status)
        result = LeaveStateMachine.process_unit_head_review(current, recommended=recommended)
        if not result.is_valid:
            raise InvalidLeaveTransitionError(result.message)

        prev_status = req.status
        req.status = result.next_status.value
        req.unit_head_recommendation = "recommended" if recommended else "rejected"
        req.unit_head_remarks = remarks
        req.save(update_fields=["status", "unit_head_recommendation", "unit_head_remarks", "updated_at"])

        LeaveTransitionHistory.objects.create(
            leave_request=req,
            from_status=prev_status,
            to_status=result.next_status.value,
            actor_user_id=unit_head_user_id,
            remarks=f"Unit Head {'recommended' if recommended else 'rejected'}. {remarks}".strip(),
        )
        return req


def sanction_leave(
    *,
    leave_id: int,
    authority_user_id: int,
    approved: bool,
    remarks: str = "",
) -> LeaveRequest:
    """Record final sanction decision by Competent Authority and deduct quota on approval."""
    with transaction.atomic():
        req = LeaveRequest.objects.select_for_update().get(pk=leave_id)
        current = LeaveStatus(req.status)
        result = LeaveStateMachine.process_sanction_decision(current, approved=approved)
        if not result.is_valid:
            raise InvalidLeaveTransitionError(result.message)

        prev_status = req.status
        req.status = result.next_status.value
        req.sanction_remarks = remarks
        req.sanctioning_authority_user_id = authority_user_id

        if approved:
            req.sanctioned_at = timezone.now()
            # Deduct availed balance atomically
            deduct_balance(
                user_id=req.user_id,
                year=req.start_date.year,
                category=req.category,
                days=float(req.days_calculated),
                reason=f"Sanctioned Leave #{req.id} ({req.start_date} to {req.end_date})",
            )

        req.save(update_fields=[
            "status",
            "sanction_remarks",
            "sanctioning_authority_user_id",
            "sanctioned_at",
            "updated_at",
        ])

        LeaveTransitionHistory.objects.create(
            leave_request=req,
            from_status=prev_status,
            to_status=result.next_status.value,
            actor_user_id=authority_user_id,
            remarks=f"Sanctioning authority {'approved' if approved else 'rejected'}. {remarks}".strip(),
        )
        return req
