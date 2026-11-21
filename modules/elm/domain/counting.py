"""Leave day counting logic.

Enforces:
- BR-EL-010: Half-day CL treatment (0.5 day)
- BR-EL-011: Continuous-day counting for EL, COL, and VL (intervening weekends and
  closed holidays count); exclusion of CL, SCL, and RH from continuous counting.
"""
from __future__ import annotations

from collections.abc import Set
from datetime import date, timedelta
from decimal import Decimal

from modules.elm.domain.constants import (
    CONTINUOUS_COUNTING_CATEGORIES,
    LeaveCategory,
)


def calculate_chargeable_days(
    category: str | LeaveCategory,
    start_date: date,
    end_date: date,
    *,
    is_half_day: bool = False,
    closed_holidays: Set[date] | None = None,
) -> Decimal:
    """Calculate chargeable leave days for a requested interval.

    Args:
        category: The leave category (CL, RH, SCL, EL, COL, VL).
        start_date: Start date of leave (inclusive).
        end_date: End date of leave (inclusive).
        is_half_day: Whether the leave is half-day (only valid for CL).
        closed_holidays: Set of closed holiday dates falling within the calendar.

    Returns:
        Decimal count of chargeable leave days.
    """
    if end_date < start_date:
        raise ValueError("End date cannot be earlier than start date.")

    cat = LeaveCategory(category) if isinstance(category, str) else category
    closed_holidays_set = closed_holidays or set()

    if is_half_day:
        if cat != LeaveCategory.CL:
            raise ValueError("Half-day leave is only supported for Casual Leave (CL).")
        if start_date != end_date:
            raise ValueError("Half-day leave must start and end on the same date.")
        # BR-EL-010: Half-day CL consumes 0.5 days
        return Decimal("0.5")

    # BR-EL-011: For EL, COL, and VL, intervening weekends and closed holidays
    # count as leave days (continuous counting).
    if cat in CONTINUOUS_COUNTING_CATEGORIES:
        total_calendar_days = (end_date - start_date).days + 1
        return Decimal(str(total_calendar_days))

    # For CL, RH, and SCL: intervening weekends and closed holidays do NOT count
    chargeable = 0
    curr = start_date
    one_day = timedelta(days=1)

    while curr <= end_date:
        # 5 = Saturday, 6 = Sunday
        is_weekend = curr.weekday() in (5, 6)
        is_closed_holiday = curr in closed_holidays_set

        if not is_weekend and not is_closed_holiday:
            chargeable += 1

        curr += one_day

    return Decimal(str(chargeable))
