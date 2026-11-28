"""Resumption of duty submission and verification service."""

from __future__ import annotations

import datetime

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.leave.domain.counting import count_leave_days
from modules.leave.domain.state_machine import LeaveEvent, LeaveState
from modules.leave.models import LeaveRequest, LedgerEntry
from modules.leave.selectors.calendars import get_active_calendar, get_calendar_holidays
from modules.leave.services.state import advance_request_state


def submit_resumption(
    request_id: int,
    user_id: int,
    resumed_on: datetime.date,
    remark: str = "",
) -> LeaveRequest:
    """Submits resumption of duty report under EL-UC-010 and BR-EL-027."""
    req = LeaveRequest.objects.filter(pk=request_id).first()
    if not req:
        raise NotFoundError(f"Leave request #{request_id} does not exist.")

    if req.user_id != user_id:
        raise PermissionDeniedError("Only the applicant can report duty resumption.")

    if req.category not in ("EL", "COL", "VL"):
        raise ConflictError("Resumption applies only to EL, COL, and VL categories.")

    if req.state != LeaveState.APPROVED:
        raise ConflictError(f"Cannot submit resumption for leave in state '{req.state}'.")

    req.resumed_on = resumed_on
    req.save(update_fields=["resumed_on", "updated_at"])

    return advance_request_state(
        request_id=request_id,
        event=LeaveEvent.SUBMIT_RESUMPTION,
        actor_user_id=user_id,
        actor_role="Employee",
        remark=remark,
        workflow_ref="CW-EL-04",
    )


def verify_resumption(
    request_id: int,
    verifier_user_id: int,
    verifier_role: str,
    remark: str = "",
) -> LeaveRequest:
    """Verifies resumption and adjusts leave ledger under EL-UC-011 and BR-EL-028."""
    req = LeaveRequest.objects.filter(pk=request_id).first()
    if not req:
        raise NotFoundError(f"Leave request #{request_id} does not exist.")

    if req.state != LeaveState.RESUMPTION_PENDING:
        raise ConflictError(
            f"Request is not pending resumption review (current state: {req.state})."
        )

    actual_end = (req.resumed_on - datetime.timedelta(days=1)) if req.resumed_on else req.ends_on
    calendar = get_active_calendar(req.starts_on.year)
    holidays = get_calendar_holidays(calendar) if calendar else set()
    actual_days = count_leave_days(req.category, req.starts_on, actual_end, req.half, holidays)

    req.actual_days = actual_days
    req.save(update_fields=["actual_days", "updated_at"])

    # BR-EL-028: Normal, early, and late resumption outcome
    diff = req.requested_days - actual_days
    if diff != 0:
        LedgerEntry.objects.create(
            user_id=req.user_id,
            year=req.starts_on.year,
            category=req.category,
            days=diff,
            reason="resumption_adjustment",
            request_id=req.pk,
            note=f"Resumption adjustment for request {req.pk} ({diff} days)",
        )

    return advance_request_state(
        request_id=request_id,
        event=LeaveEvent.VERIFY_RESUMPTION,
        actor_user_id=verifier_user_id,
        actor_role=verifier_role,
        remark=remark,
        workflow_ref="CW-EL-04",
    )
