"""Leave day calculation logic (BR-EL-010, BR-EL-011)."""
from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Set

from modules.leave.domain.exceptions import InvalidLeaveCalculation
from modules.leave.domain.categories import (
    CL,
    CONTINUOUS_COUNT_CATEGORIES,
    RH,
)


def calculate_leave_days(
    category: str,
    start_date: datetime.date,
    end_date: datetime.date,
    half_day_type: str = "full",
    closed_holidays: Set[datetime.date] | None = None,
    rh_holidays: Set[datetime.date] | None = None,
) -> Decimal:
    """Calculate the deductible days count for a given leave range.

    BR-EL-010: Half-day CL counts as 0.5.
    BR-EL-011: EL, COL, and VL are counted continuously across the approved interval
               including weekends and holidays.
               CL, SCL, and RH exclude weekends and closed holidays.
    BR-EL-003: RH must correspond to an applicable Restricted Holiday in the calendar.
    """
    if end_date < start_date:
        raise InvalidLeaveCalculation("End date cannot be earlier than start date.")

    if half_day_type in ("first_half", "second_half"):
        if category != CL:
            raise InvalidLeaveCalculation("Half-day leave is only permitted for Casual Leave (CL).")
        if start_date != end_date:
            raise InvalidLeaveCalculation("Half-day leave must start and end on the same single date.")
        return Decimal("0.5")

    if category in CONTINUOUS_COUNT_CATEGORIES:
        # Continuous-day counting: all calendar days count
        total_days = (end_date - start_date).days + 1
        return Decimal(str(total_days))

    # Working-day counting for CL, SCL, RH
    closed_holidays = closed_holidays or set()
    total_days = 0
    curr = start_date
    one_day = datetime.timedelta(days=1)

    while curr <= end_date:
        # 5 = Saturday, 6 = Sunday
        is_weekend = curr.weekday() in (5, 6)
        is_closed = curr in closed_holidays
        if not is_weekend and not is_closed:
            total_days += 1
        curr += one_day

    if category == RH:
        rh_holidays = rh_holidays or set()
        if start_date != end_date:
            raise InvalidLeaveCalculation("Restricted Holiday must be taken 1 day at a time.")
        if start_date not in rh_holidays:
            raise InvalidLeaveCalculation(
                f"Date {start_date} is not listed as an active Restricted Holiday (RH)."
            )
        return Decimal("1.0")

    if total_days == 0:
        raise InvalidLeaveCalculation(
            "Selected dates fall entirely on weekends or closed holidays."
        )

    return Decimal(str(total_days))
