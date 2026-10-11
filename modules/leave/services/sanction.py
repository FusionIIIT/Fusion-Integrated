"""Sanctioning service for competent authority final decisions.

Implements EL-UC-005, BR-EL-004, BR-EL-018, BR-EL-019, BR-EL-020.
"""

from django.db import transaction

from core.api.exceptions import BadRequestError
from fusion_auth.principal import Principal
from modules.leave.domain.constants import Event
from modules.leave.models.requests import LeaveRequest
from modules.leave.models.sla import SlaTaskClock
from modules.leave.selectors.requests import get_request_by_id
from modules.leave.services.transitions import execute_transition


def sanction_leave_request(
    request_id: int,
    action: str,  # "approve" or "reject"
    principal: Principal,
    remarks: str = "",
) -> LeaveRequest:
    """Competent authority makes final approval or rejection decision (EL-UC-005)."""
    req = get_request_by_id(request_id, principal)

    if action not in ("approve", "reject"):
        raise BadRequestError("Sanctioning decision must be 'approve' or 'reject'.")

    event = Event.APPROVE if action == "approve" else Event.REJECT
    actor_role = "director" if principal.active_role == "Director" else "sanctioning_authority"

    # Stop active sanction SLA clock
    with transaction.atomic():
        SlaTaskClock.objects.filter(
            request=req,
            task_type="sanction_decision",
            is_pending=True,
        ).update(is_pending=False)

        req = execute_transition(
            request_id=req.id,
            event=event,
            actor_user_id=principal.user_id,
            actor_role=actor_role,
            remarks=remarks or f"Final sanctioning decision: {action}",
        )

        return req
