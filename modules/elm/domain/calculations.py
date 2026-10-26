"""Pure Python business calculations for ELM.

Encapsulates leave-day counting rules, half-day CL calculations,
VL-to-EL conversions, and overlap validations.
Zero framework dependencies.
"""
from __future__ import annotations

from collections.abc import Set
from datetime import date, timedelta

from ..entities import LeaveCategory
from ..errors import LeaveValidationError

def calculate_leave_days(
    category: str | LeaveCategory,
    start_date: date,
    end_date: date,
    is_half_day: bool = False,
    half_day_period: str | None = None,
    closed_holidays: Set[date] | None = None,
) -> float:
    """Calculate the net leave days consumed by an application.

    Rules implemented:
    - BR-EL-010: Half-day CL consumes exactly 0.5 days.
    - BR-EL-011: Continuous counting for EL, VL, COL includes intervening weekends & holidays.
    - BR-EL-011: CL, SCL, RH exclude weekends (Saturday, Sunday) and closed holidays.
    """
    """Calculate the net leave days consumed by an application.

    Parameters
    ----------
    category: str | LeaveCategory
        Leave category (string or enum).
    start_date: date
        Start date of the leave.
    end_date: date
        End date of the leave (inclusive).
    is_half_day: bool, default False
        Whether the leave is a half‑day.
    half_day_period: str | None, default None
        "AM" or "PM" indicator (currently unused).
    closed_holidays: Set[date] | None, default None
        Set of dates that are holidays and should be excluded where applicable.

    Returns
    -------
    float
        Number of leave days counted.

    Raises
    ------
    LeaveValidationError
        For invalid date ranges or half‑day rule violations.
    """
    if start_date > end_date:
        raise LeaveValidationError("start_date cannot be after end_date.")

    cat_str = category.value if isinstance(category, LeaveCategory) else str(category)

    # Half‑day rule for CL and SCL (BR‑EL‑010)
    if cat_str in (LeaveCategory.CL.value, LeaveCategory.SCL.value) and is_half_day:
        if start_date != end_date:
            raise LeaveValidationError(f"Half‑day {cat_str} must have identical start and end dates.")
        return 0.5

    # Continuous counting for EL, VL, COL (BR‑EL‑011)
    if cat_str in (LeaveCategory.EL.value, LeaveCategory.VL.value, LeaveCategory.COL.value):
        total_calendar_days = (end_date - start_date).days + 1
        # Exclude closed holidays if provided
        if closed_holidays:
            holiday_count = sum(1 for d in closed_holidays if start_date <= d <= end_date)
            total_calendar_days -= holiday_count
        return float(total_calendar_days)

    # Working-day counting for CL, SCL, RH (exclude weekends and closed holidays)
    holidays = closed_holidays or set()
    current = start_date
    working_days = 0

    while current <= end_date:
        # 5 is Saturday, 6 is Sunday
        if current.weekday() < 5 and current not in holidays:
            working_days += 1
        current += timedelta(days=1)

    return float(working_days)


def calculate_vl_to_el_conversion(unused_vl: float) -> float:
    """Calculate year-end conversion of Faculty Vacation Leave to Earned Leave.

    Rule BR-EL-007: All unused VL converts to EL at 2 VL : 1 EL.
    Fractional conversion is supported (e.g. 15 VL -> 7.5 EL).
    """
    if unused_vl <= 0:
        return 0.0
    return float(unused_vl / 2.0)


def check_date_overlap(
    start1: date,
    end1: date,
    start2: date,
    end2: date,
) -> bool:
    """Check whether two closed date intervals [start1, end1] and [start2, end2] overlap."""
    return max(start1, start2) <= min(end1, end2)
