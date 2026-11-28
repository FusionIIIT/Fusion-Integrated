"""Leave day calculation rules."""

from __future__ import annotations

import datetime
from decimal import Decimal

from .errors import LeavePolicyViolationError

CONTINUOUS_CATEGORIES = frozenset({"EL", "COL", "VL"})
WORKING_DAY_CATEGORIES = frozenset({"CL", "SCL", "RH"})


def count_leave_days(
    category: str,
    starts_on: datetime.date,
    ends_on: datetime.date,
    half: str = "none",
    holidays: set[datetime.date] | None = None,
) -> Decimal:
    """Calculates leave days according to BR-EL-010 and BR-EL-011."""
    if starts_on > ends_on:
        raise LeavePolicyViolationError("Start date cannot be after end date.")

    if half != "none":
        if starts_on != ends_on:
            raise LeavePolicyViolationError("Half-day leave must start and end on the same date.")
        if category != "CL":
            raise LeavePolicyViolationError("Half-day is admissible only for Casual Leave.")
        return Decimal("0.5")

    if category in CONTINUOUS_CATEGORIES:
        return Decimal((ends_on - starts_on).days + 1)

    holidays_set = holidays or set()
    total_days = 0
    curr = starts_on
    one_day = datetime.timedelta(days=1)
    while curr <= ends_on:
        # Exclude Saturdays (5) and Sundays (6) and closed holidays
        if curr.weekday() < 5 and curr not in holidays_set:
            total_days += 1
        curr += one_day

    return Decimal(total_days)
