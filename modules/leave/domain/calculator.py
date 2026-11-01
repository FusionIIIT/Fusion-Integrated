"""Calculation logic for leave days.

Pure Python — no Django, DRF or Celery imports permitted.
Conforms to BR-EL-010 (Half-day CL) and BR-EL-011 (Continuous-day counting).
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, Set

from modules.leave.domain.constants import HalfDayOption, LeaveCategory


def calculate_leave_days(
    category: str | LeaveCategory,
    start_date: date,
    end_date: date,
    half_day: Optional[str | HalfDayOption] = None,
    closed_dates: Optional[Set[date]] = None,
) -> Decimal:
    """Calculate the number of leave days consumed by a requested interval.

    Rules:
    - BR-EL-010: Half-day CL consumes exactly 0.5 days. Start date must equal end date.
    - BR-EL-011: For EL, COL, and VL, intervening weekends and closed holidays inside
      the continuous approved interval COUNT as leave days.
      For CL, SCL, and RH, intervening weekends (Saturday & Sunday) and closed holidays
      do NOT count as leave days.
    """
    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date")

    cat = LeaveCategory(category)
    half = HalfDayOption(half_day) if half_day else HalfDayOption.NONE

    # Half-day check (only CL supports half day per BR-EL-010)
    if half in (HalfDayOption.FIRST_HALF, HalfDayOption.SECOND_HALF):
        if cat != LeaveCategory.CL:
            raise ValueError(f"Half-day leave is only supported for Casual Leave (CL), not {cat.value}")
        if start_date != end_date:
            raise ValueError("Half-day leave must start and end on the same single date")
        return Decimal("0.5")

    # Continuous counting for EL, COL, VL
    if cat in (LeaveCategory.EL, LeaveCategory.COL, LeaveCategory.VL):
        total_days = (end_date - start_date).days + 1
        return Decimal(str(total_days))

    # Working-day counting for CL, SCL, RH
    closed = closed_dates or set()
    working_days = 0
    cur = start_date
    while cur <= end_date:
        # 5 = Saturday, 6 = Sunday in Python weekday()
        is_weekend = cur.weekday() in (5, 6)
        is_closed = cur in closed
        if not (is_weekend or is_closed):
            working_days += 1
        cur += timedelta(days=1)

    return Decimal(str(working_days))
