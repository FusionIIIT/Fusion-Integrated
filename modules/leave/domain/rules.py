"""Pure leave policy rules; persistence and permissions live elsewhere."""

from datetime import date


class LeaveRuleError(ValueError):
    """A requested leave operation violates a domain rule."""


def requested_days(start: date, end: date) -> int:
    """Count weekdays in an inclusive date range (public holidays are not modeled)."""
    if end < start:
        raise LeaveRuleError("The end date must be on or after the start date.")
    return sum(1 for offset in range((end - start).days + 1)
               if date.fromordinal(start.toordinal() + offset).weekday() < 5)


def validate_request(start: date, end: date, available_days: int) -> int:
    days = requested_days(start, end)
    if days == 0:
        raise LeaveRuleError("The selected date range contains no working days.")
    if days > available_days:
        raise LeaveRuleError("The request exceeds the available leave balance.")
    return days
