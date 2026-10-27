"""Leave calculation engine implementing BR-EL-002..011."""
from datetime import date, timedelta
from typing import Set

CONTINUOUS_COUNTING_CATEGORIES = {"EL", "COL", "VL"}
WORKING_DAY_COUNTING_CATEGORIES = {"CL", "SCL", "RH"}


def calculate_leave_days(
    category: str,
    start_date: date,
    end_date: date,
    half_day: str = "none",
    closed_holidays: Set[date] | None = None,
) -> float:
    """Calculate the number of leave days consumed by a requested interval.

    Rules applied:
    - BR-EL-010: Half-day CL consumes 0.5 days.
    - BR-EL-011: For EL, COL, and VL, intervening weekends and closed holidays count continuously.
    - For CL, SCL, and RH, weekends (Saturday, Sunday) and closed holidays are excluded.
    """
    if start_date > end_date:
        raise ValueError("Start date cannot be after end date.")

    if category == "CL" and half_day in ("first_half", "second_half"):
        if start_date != end_date:
            raise ValueError("Half-day Casual Leave can only be applied for a single calendar date.")
        return 0.5

    # Continuous counting for EL, COL, VL
    if category in CONTINUOUS_COUNTING_CATEGORIES:
        return float((end_date - start_date).days + 1)

    # Working day counting for CL, SCL, RH
    closed_holidays = closed_holidays or set()
    days_count = 0
    curr = start_date
    while curr <= end_date:
        # 5 = Saturday, 6 = Sunday
        is_weekend = curr.weekday() in (5, 6)
        is_holiday = curr in closed_holidays
        if not is_weekend and not is_holiday:
            days_count += 1
        curr += timedelta(days=1)

    return float(days_count)


def calculate_vl_to_el_conversion(unused_vl: float, ratio: float = 0.5) -> float:
    """Year-end conversion of unused faculty Vacation Leave (VL) to Earned Leave (EL).

    BR-EL-007: At year end, all unused faculty VL converts to EL at 2 VL : 1 EL,
    including fractional conversion.
    """
    if unused_vl <= 0:
        return 0.0
    return round(unused_vl * ratio, 2)
