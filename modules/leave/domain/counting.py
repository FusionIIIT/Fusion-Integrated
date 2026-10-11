from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from modules.leave.domain.categories import CONTINUOUS


def count_days(
    category: str, start: date, end: date, is_half_day: bool, holidays: set[date]
) -> Decimal:
    """Count leave days based on category, start, end, is_half_day, and holidays (EL-UC-001/BR-EL-010, BR-EL-011)."""
    if is_half_day:
        return Decimal("0.5")

    if category in CONTINUOUS:
        return Decimal((end - start).days + 1)

    working_days = 0
    current_date = start
    while current_date <= end:
        if current_date.weekday() < 5 and current_date not in holidays:
            working_days += 1
        current_date += timedelta(days=1)

    return Decimal(working_days)


def overlaps(a_start, a_end, b_start, b_end) -> bool:
    """Check if two date ranges overlap (EL-UC-001/BR-EL-012)."""
    return a_start <= b_end and a_end >= b_start
