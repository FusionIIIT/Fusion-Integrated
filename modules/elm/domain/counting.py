"""Leave-day counting rules for ELM.

Pure Python: no Django dependencies.
Enforces BR-EL-010 (Half-day CL) and BR-EL-011 (Continuous-day counting).
"""
from __future__ import annotations

import datetime
from typing import Container

from modules.elm.domain.constants import CONTINUOUS_COUNT_CATEGORIES, HalfDayPeriod, LeaveCategory


class InvalidDateRange(ValueError):
    """Raised when start_date is after end_date."""


class InvalidHalfDayRequest(ValueError):
    """Raised when half-day parameters are inconsistent."""


def is_weekend(d: datetime.date) -> bool:
    """Saturday (5) and Sunday (6) are standard weekend days."""
    return d.weekday() in (5, 6)


def calculate_chargeable_days(
    category: str | LeaveCategory,
    start_date: datetime.date,
    end_date: datetime.date,
    is_half_day: bool = False,
    half_day_period: str | HalfDayPeriod = HalfDayPeriod.NONE,
    closed_holidays: Container[datetime.date] | None = None,
) -> float:
    """Calculate chargeable leave days according to category and calendar rules.

    BR-EL-010: CL supports first-half and second-half, consuming exactly 0.5 day.
    BR-EL-011: For EL, COL, and VL, intervening weekends and closed holidays
    inside the continuous interval count as leave days (continuous count).
    For CL, SCL, and RH, intervening weekends and closed holidays are excluded
    (working days count).
    """
    if end_date < start_date:
        raise InvalidDateRange(f"end_date ({end_date}) is before start_date ({start_date}).")

    cat = LeaveCategory(category)
    holidays = closed_holidays or set()

    # Half-day validation (BR-EL-010)
    if is_half_day:
        if cat != LeaveCategory.CL:
            raise InvalidHalfDayRequest("Half-day leave is only permitted for Casual Leave (CL).")
        if start_date != end_date:
            raise InvalidHalfDayRequest("Half-day leave must start and end on the same calendar date.")
        period = HalfDayPeriod(half_day_period)
        if period not in (HalfDayPeriod.FIRST_HALF, HalfDayPeriod.SECOND_HALF):
            raise InvalidHalfDayRequest("Half-day leave requires specifying FIRST_HALF or SECOND_HALF.")
        # An approved half-day consumes exactly 0.5 CL day
        return 0.5

    # Continuous counting for EL, COL, VL (BR-EL-011)
    if cat in CONTINUOUS_COUNT_CATEGORIES:
        return float((end_date - start_date).days + 1)

    # Working-day counting for CL, SCL, RH
    chargeable = 0
    curr = start_date
    one_day = datetime.timedelta(days=1)
    while curr <= end_date:
        # Intervening weekends and closed holidays inside CL/SCL/RH are NOT counted
        if not is_weekend(curr) and curr not in holidays:
            chargeable += 1
        curr += one_day

    return float(chargeable)
