"""Leave-day counting domain rules (Section 4)."""
from datetime import date, timedelta
from decimal import Decimal

from modules.elm.domain.constants import (
    CL,
    CONTINUOUS_COUNT_CATEGORIES,
    HALF_DAY_FIRST,
    HALF_DAY_SECOND,
)


def calculate_leave_days(
    category: str,
    start_date: date,
    end_date: date,
    half_day_type: str = "",
    closed_holidays: set[date] | None = None,
) -> Decimal:
    """Calculate the leave day count according to Section 4.

    - For EL, COL, and VL, leave is counted continuously across the approved
      interval. Intervening weekends and closed holidays within the interval
      count as leave days.
    - For CL, SCL, and RH, intervening weekends and closed holidays do not count.
    - For CL, half-day leave (first-half or second-half) consumes 0.5 days on a single date.
    """
    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date.")

    if category == CL and half_day_type in (HALF_DAY_FIRST, HALF_DAY_SECOND):
        if start_date != end_date:
            raise ValueError("Half-day CL must be for a single date.")
        return Decimal("0.5")

    total_days = (end_date - start_date).days + 1

    if category in CONTINUOUS_COUNT_CATEGORIES:
        return Decimal(str(total_days))

    # Discrete counting for CL, SCL, RH: exclude weekends and closed holidays
    holidays = closed_holidays or set()
    countable_days = 0
    curr = start_date
    while curr <= end_date:
        # 5 = Saturday, 6 = Sunday
        is_weekend = curr.weekday() in (5, 6)
        is_closed_holiday = curr in holidays
        if not is_weekend and not is_closed_holiday:
            countable_days += 1
        curr += timedelta(days=1)

    return Decimal(str(countable_days))
