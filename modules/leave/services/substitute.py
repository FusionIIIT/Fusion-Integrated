"""Substitute response and renomination service."""

from __future__ import annotations

from core.api.exceptions import ConflictError, DomainError, NotFoundError, PermissionDeniedError
from modules.leave.domain import errors, rules
from modules.leave.domain.state_machine import LeaveEvent
from modules.leave.models import LeaveRequest
from modules.leave.selectors.requests import check_substitute_availability
from modules.leave.services.state import advance_request_state


def respond_substitute_nomination(
    request_id: int,
    substitute_user_id: int,
    accepted: bool,
    remark: str = "",
) -> LeaveRequest:
    """Handles substitute accept/decline under EL-UC-002 and BR-EL-015."""
    req = LeaveRequest.objects.filter(pk=request_id).first()
    if not req:
        raise NotFoundError(f"Leave request #{request_id} does not exist.")

    if req.substitute_user_id != substitute_user_id:
        raise PermissionDeniedError("You are not the nominated substitute for this request.")

    event = LeaveEvent.SUBSTITUTE_ACCEPT if accepted else LeaveEvent.SUBSTITUTE_DECLINE
    return advance_request_state(
        request_id=request_id,
        event=event,
        actor_user_id=substitute_user_id,
        actor_role="Substitute",
        remark=remark,
        workflow_ref="CW-EL-01",
    )


def renominate_substitute(
    request_id: int,
    user_id: int,
    new_substitute_id: int,
) -> LeaveRequest:
    """Renominates substitute after decline under EL-UC-019."""
    req = LeaveRequest.objects.filter(pk=request_id).first()
    if not req:
        raise NotFoundError(f"Leave request #{request_id} does not exist.")

    if req.user_id != user_id:
        raise PermissionDeniedError("Only the applicant can renominate a substitute.")

    try:
        rules.validate_substitute(user_id, new_substitute_id)
    except errors.LeaveDomainError as e:
        raise DomainError(str(e), code=e.code) from e

    if not check_substitute_availability(new_substitute_id, req.starts_on, req.ends_on):
        raise ConflictError(
            "The nominated substitute has conflicting active leave during this period."
        )

    req.substitute_user_id = new_substitute_id
    req.save(update_fields=["substitute_user_id", "updated_at"])

    return advance_request_state(
        request_id=request_id,
        event=LeaveEvent.RENOMINATE,
        actor_user_id=user_id,
        actor_role="Employee",
        remark=f"Renominated substitute to {new_substitute_id}",
        workflow_ref="CW-EL-01",
    )
