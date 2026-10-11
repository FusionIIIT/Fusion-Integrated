"""Leave-day counting arithmetic (pure Python).

Implements BR-EL-010 (half-day CL) and BR-EL-011 (continuous-day counting).
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal


def calculate_leave_days(
    start_date: date,
    end_date: date,
    is_continuous: bool = False,
    closed_holidays: set[date] | None = None,
    is_half_day: bool = False,
) -> Decimal:
    """Calculate the billable leave days between start_date and end_date (inclusive).

    BR-EL-010: Half-day CL consumes exactly 0.5 day.
    BR-EL-011: For EL, COL, and VL, intervening weekends and closed holidays count.
               For CL, SCL, and RH, weekends and closed holidays do NOT count.
    """
    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date")

    if is_half_day:
        if start_date != end_date:
            raise ValueError("Half-day leave must have identical start and end dates")
        return Decimal("0.5")

    total_days = Decimal("0.0")
    holidays = closed_holidays or set()
    current = start_date
    one_day = timedelta(days=1)

    while current <= end_date:
        if is_continuous:
            # Continuous-day counting: all calendar days count
            total_days += Decimal("1.0")
        else:
            # Working-day counting: exclude Saturdays, Sundays, and closed holidays
            is_weekend = current.weekday() in (5, 6)
            is_holiday = current in holidays
            if not is_weekend and not is_holiday:
                total_days += Decimal("1.0")
        current += one_day

    return total_days
