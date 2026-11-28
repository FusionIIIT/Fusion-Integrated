"""Final sanctioning decision service."""

from __future__ import annotations

from core.api.exceptions import NotFoundError
from modules.leave.domain.state_machine import LeaveEvent, LeaveState
from modules.leave.models import LeaveRequest
from modules.leave.services.state import advance_request_state


def sanction_leave_request(
    request_id: int,
    actor_user_id: int,
    actor_role: str,
    approve: bool,
    remark: str = "",
) -> LeaveRequest:
    """Takes the final sanctioning decision under EL-UC-005."""
    req = LeaveRequest.objects.filter(pk=request_id).first()
    if not req:
        raise NotFoundError(f"Leave request #{request_id} does not exist.")

    if req.state == LeaveState.CANCELLATION_PENDING_SANCTION:
        event = LeaveEvent.CANCEL_SANCTION_APPROVE if approve else LeaveEvent.CANCEL_SANCTION_REJECT
    elif req.state == LeaveState.EXTENSION_PENDING_SANCTION:
        event = LeaveEvent.EXT_SANCTION_APPROVE if approve else LeaveEvent.EXT_SANCTION_REJECT
    else:
        event = LeaveEvent.SANCTION_APPROVE if approve else LeaveEvent.SANCTION_REJECT

    return advance_request_state(
        request_id=request_id,
        event=event,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        remark=remark,
        workflow_ref="CW-EL-01",
    )
