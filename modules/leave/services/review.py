"""Unit Head review service."""

from __future__ import annotations

from core.api.exceptions import NotFoundError
from modules.leave.domain.state_machine import LeaveEvent, LeaveState
from modules.leave.models import LeaveRequest
from modules.leave.services.state import advance_request_state


def review_leave_request(
    request_id: int,
    reviewer_user_id: int,
    reviewer_role: str,
    approve: bool,
    remark: str = "",
) -> LeaveRequest:
    """Handles Unit Head review/recommendation under EL-UC-003, BR-EL-016, and BR-EL-017."""
    req = LeaveRequest.objects.filter(pk=request_id).first()
    if not req:
        raise NotFoundError(f"Leave request #{request_id} does not exist.")

    is_cl_rh = req.category in ("CL", "RH")

    if req.state == LeaveState.PENDING_REVIEW:
        if is_cl_rh:
            event = LeaveEvent.UH_APPROVE if approve else LeaveEvent.UH_REJECT
        else:
            req.unit_head_recommended = approve
            req.save(update_fields=["unit_head_recommended", "updated_at"])
            event = LeaveEvent.UH_RECOMMEND if approve else LeaveEvent.UH_NOT_RECOMMEND

    elif req.state == LeaveState.CANCELLATION_PENDING_REVIEW:
        if is_cl_rh:
            event = LeaveEvent.CANCEL_UH_APPROVE if approve else LeaveEvent.CANCEL_UH_REJECT
        else:
            event = (
                LeaveEvent.CANCEL_UH_RECOMMEND if approve else LeaveEvent.CANCEL_UH_NOT_RECOMMEND
            )

    elif req.state == LeaveState.EXTENSION_PENDING_REVIEW:
        event = LeaveEvent.EXT_UH_RECOMMEND if approve else LeaveEvent.EXT_UH_NOT_RECOMMEND

    else:
        event = LeaveEvent.UH_APPROVE if approve else LeaveEvent.UH_REJECT

    return advance_request_state(
        request_id=request_id,
        event=event,
        actor_user_id=reviewer_user_id,
        actor_role=reviewer_role,
        remark=remark,
        workflow_ref="CW-EL-01",
    )
