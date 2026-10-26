"""Leave day counting algorithms adhering to BR-EL-011 and BR-EL-012."""

from datetime import date, timedelta
from decimal import Decimal

from .entities import HalfDayType, LeaveCategory
from .errors import InvalidDateRangeError


def calculate_leave_days(
    category: str,
    start_date: date,
    end_date: date,
    half_day_type: str = HalfDayType.FULL.value,
    closed_holiday_dates: set[date] | None = None,
) -> Decimal:
    """Calculate the number of leave days for a given period and category.

    Rules:
    - BR-EL-011: CL supports first-half and second-half requests consuming 0.5 days.
      Half-day request must have start_date == end_date.
    - BR-EL-012: For EL, COL, and VL, leave is counted continuously across the
      approved interval (intervening weekends and closed holidays count as leave days).
    - For CL, SCL, and RH, intervening weekends (Saturday, Sunday) and closed holidays
      do NOT count as leave days (only working days count).
    """
    if end_date < start_date:
        raise InvalidDateRangeError("End date cannot be earlier than start date.")

    # Half day CL
    if category == LeaveCategory.CL.value and half_day_type in (
        HalfDayType.FIRST_HALF.value,
        HalfDayType.SECOND_HALF.value,
    ):
        if start_date != end_date:
            raise InvalidDateRangeError("Half-day leave must be for a single day.")
        return Decimal("0.5")

    # Continuous counting categories: EL, COL, VL
    if category in (LeaveCategory.EL.value, LeaveCategory.COL.value, LeaveCategory.VL.value):
        total_days = (end_date - start_date).days + 1
        return Decimal(str(total_days))

    # Working day counting categories: CL, SCL, RH
    closed_dates = closed_holiday_dates or set()
    working_days = 0
    curr = start_date
    while curr <= end_date:
        # Weekend check: 5 is Saturday, 6 is Sunday
        if curr.weekday() not in (5, 6) and curr not in closed_dates:
            working_days += 1
        curr += timedelta(days=1)

    return Decimal(str(working_days))
