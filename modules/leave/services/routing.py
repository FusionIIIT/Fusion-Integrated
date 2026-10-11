"""Higher-sanction routing service."""

from __future__ import annotations

from core.api.exceptions import NotFoundError
from modules.leave.domain.state_machine import LeaveEvent, LeaveState
from modules.leave.models import LeaveRequest
from modules.leave.services.state import advance_request_state


def route_leave_request(
    request_id: int,
    actor_user_id: int,
    actor_role: str,
    remark: str = "",
) -> LeaveRequest:
    """Verifies and routes request to final sanction authority under EL-UC-004."""
    req = LeaveRequest.objects.filter(pk=request_id).first()
    if not req:
        raise NotFoundError(f"Leave request #{request_id} does not exist.")

    if req.state == LeaveState.CANCELLATION_PENDING_ROUTING:
        event = LeaveEvent.CANCEL_ROUTE
    elif req.state == LeaveState.EXTENSION_PENDING_ROUTING:
        event = LeaveEvent.EXT_ROUTE
    else:
        event = LeaveEvent.ROUTE

    return advance_request_state(
        request_id=request_id,
        event=event,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        remark=remark,
        workflow_ref="CW-EL-01",
    )
