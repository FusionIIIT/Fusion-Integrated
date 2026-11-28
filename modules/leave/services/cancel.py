"""Approved leave cancellation service."""

from __future__ import annotations

import datetime

from core.api.exceptions import ConflictError, DomainError, NotFoundError, PermissionDeniedError
from modules.leave.domain import errors, rules
from modules.leave.domain.state_machine import LeaveEvent, LeaveState
from modules.leave.models import LeaveRequest
from modules.leave.services.state import advance_request_state


def request_cancellation(
    request_id: int,
    user_id: int,
    remark: str = "",
) -> LeaveRequest:
    """Submits pre-start cancellation request under EL-UC-008 and BR-EL-023."""
    req = LeaveRequest.objects.filter(pk=request_id).first()
    if not req:
        raise NotFoundError(f"Leave request #{request_id} does not exist.")

    if req.user_id != user_id:
        raise PermissionDeniedError(
            "Only the applicant can request cancellation of approved leave."
        )

    if req.state != LeaveState.APPROVED:
        raise ConflictError(f"Cannot request cancellation for leave in state '{req.state}'.")

    try:
        rules.validate_cancellation_before_start(req.starts_on, datetime.date.today())
    except errors.LeaveDomainError as e:
        raise DomainError(str(e), code=e.code) from e

    return advance_request_state(
        request_id=request_id,
        event=LeaveEvent.REQUEST_CANCEL,
        actor_user_id=user_id,
        actor_role="Employee",
        remark=remark,
        workflow_ref="CW-EL-02",
    )
