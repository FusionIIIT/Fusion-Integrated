"""Ongoing leave extension service."""

from __future__ import annotations

import datetime

from core.api.exceptions import ConflictError, DomainError, NotFoundError, PermissionDeniedError
from modules.leave.domain import errors, rules
from modules.leave.domain.counting import count_leave_days
from modules.leave.domain.state_machine import LeaveEvent, LeaveState
from modules.leave.models import LeaveRequest
from modules.leave.selectors.balances import get_user_balance
from modules.leave.selectors.calendars import get_active_calendar, get_calendar_holidays
from modules.leave.services.state import advance_request_state


def request_extension(
    request_id: int,
    user_id: int,
    new_end: datetime.date,
    substitute_user_id: int | None = None,
    remark: str = "",
) -> LeaveRequest:
    """Requests extension of ongoing leave under EL-UC-009 and BR-EL-025."""
    req = LeaveRequest.objects.filter(pk=request_id).first()
    if not req:
        raise NotFoundError(f"Leave request #{request_id} does not exist.")

    if req.user_id != user_id:
        raise PermissionDeniedError("Only the applicant can extend their approved leave.")

    if req.state != LeaveState.APPROVED:
        raise ConflictError(f"Cannot extend leave in state '{req.state}'.")

    if new_end <= req.ends_on:
        raise ConflictError("Extended end date must be after current approved end date.")

    today = datetime.date.today()
    try:
        rules.validate_extension_admissibility(req.category, req.starts_on, today)
        rules.validate_substitute(user_id, substitute_user_id)
    except errors.LeaveDomainError as e:
        raise DomainError(str(e), code=e.code) from e

    incremental_start = req.ends_on + datetime.timedelta(days=1)
    calendar = get_active_calendar(new_end.year)
    holidays = get_calendar_holidays(calendar) if calendar else set()
    incremental_days = count_leave_days(req.category, incremental_start, new_end, "none", holidays)

    balance = get_user_balance(user_id, new_end.year, req.category)
    try:
        rules.validate_balance(balance, incremental_days)
    except errors.LeaveDomainError as e:
        raise ConflictError(str(e)) from e

    # Update request end date and requested days to reflect extension
    req.ends_on = new_end
    req.requested_days += incremental_days
    if substitute_user_id:
        req.substitute_user_id = substitute_user_id
    req.save(update_fields=["ends_on", "requested_days", "substitute_user_id", "updated_at"])

    event = LeaveEvent.REQUEST_EXTEND
    return advance_request_state(
        request_id=request_id,
        event=event,
        actor_user_id=user_id,
        actor_role="Employee",
        remark=remark,
        workflow_ref="CW-EL-03",
    )
