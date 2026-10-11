"""Leave request withdrawal service."""

from __future__ import annotations

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.leave.domain.state_machine import LeaveEvent, LeaveState
from modules.leave.models import LeaveRequest
from modules.leave.services.state import advance_request_state


def withdraw_leave_request(
    request_id: int,
    user_id: int,
    remark: str = "",
) -> LeaveRequest:
    """Withdraws a pending leave request immediately under EL-UC-007 and BR-EL-022."""
    req = LeaveRequest.objects.filter(pk=request_id).first()
    if not req:
        raise NotFoundError(f"Leave request #{request_id} does not exist.")

    if req.user_id != user_id:
        raise PermissionDeniedError("Only the applicant can withdraw their leave request.")

    if req.state in (
        LeaveState.APPROVED,
        LeaveState.REJECTED,
        LeaveState.CANCELLED,
        LeaveState.WITHDRAWN,
    ):
        raise ConflictError(f"Cannot withdraw leave request in terminal state '{req.state}'.")

    return advance_request_state(
        request_id=request_id,
        event=LeaveEvent.WITHDRAW,
        actor_user_id=user_id,
        actor_role="Employee",
        remark=remark,
        workflow_ref="CW-EL-01",
    )
