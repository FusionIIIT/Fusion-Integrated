"""Leave day counting logic according to BR-EL-010 and BR-EL-011.

Pure Python — no framework imports.
"""

from collections.abc import Set
from datetime import date, timedelta
from decimal import Decimal

from modules.leave.domain.constants import HalfDay, LeaveCategory
from modules.leave.domain.exceptions import PolicyViolationError


def calculate_leave_days(
    category: str,
    start_date: date,
    end_date: date,
    half_day: str = HalfDay.NONE,
    closed_holidays: Set[date] | None = None,
) -> Decimal:
    """Calculates leave days for a requested interval based on category rules.

    BR-EL-010: Half-day CL counts as 0.5 day (only valid for 1-day CL).
    BR-EL-011: Continuous-day counting for EL, COL, VL includes weekends/holidays.
               CL, SCL, RH count only working days (excluding weekends & closed holidays).
    """
    if start_date > end_date:
        raise PolicyViolationError("Leave start date must be on or before end date.")

    # BR-EL-010: Half-day validation
    if half_day in (HalfDay.FIRST_HALF, HalfDay.SECOND_HALF):
        if category != LeaveCategory.CL:
            raise PolicyViolationError("Half-day option is only supported for Casual Leave (CL).")
        if start_date != end_date:
            raise PolicyViolationError("Half-day Casual Leave must be a single-day request.")
        return Decimal("0.5")

    # BR-EL-011: Continuous counting for EL, COL, VL
    if category in (LeaveCategory.EL, LeaveCategory.COL, LeaveCategory.VL):
        total_days = (end_date - start_date).days + 1
        return Decimal(total_days)

    # BR-EL-011: Working-day counting for CL, SCL, RH
    holidays = closed_holidays or set()
    total_working_days = 0
    curr = start_date
    while curr <= end_date:
        # 5 = Saturday, 6 = Sunday
        if curr.weekday() < 5 and curr not in holidays:
            total_working_days += 1
        curr += timedelta(days=1)

    return Decimal(total_working_days)
