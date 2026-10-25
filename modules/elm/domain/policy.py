"""Business rules and policy validation for Leave Management (ELM).

Pure Python — no Django or HTTP dependencies.
"""
from datetime import date, timedelta
from decimal import Decimal

from modules.elm.domain.entities import LeaveInterval
from modules.elm.domain.errors import (
    IneligibleCategoryError,
    InsufficientLeaveBalanceError,
    InvalidLeaveDateError,
    InvalidSubstituteError,
    StationLeaveValidationError,
)


def calculate_leave_days(
    category_code: str,
    start_date: date,
    end_date: date,
    half_day: str = "none",
    holidays: set[date] | None = None,
) -> Decimal:
    """Calculate the deductible leave days according to category rules.

    - Half-day CL counts as 0.5 days.
    - EL, COL, and VL count continuously across the interval (weekends and
      holidays included).
    - CL, SCL, and RH exclude weekends and configured closed holidays.
    """
    if start_date > end_date:
        raise InvalidLeaveDateError("Start date cannot be after end date.")

    if half_day in ("first_half", "second_half"):
        if start_date != end_date:
            raise InvalidLeaveDateError("Half-day leave must be for a single day.")
        if category_code != "CL":
            raise InvalidLeaveDateError(
                "Half-day leave is admissible only for Casual Leave (CL)."
            )
        return Decimal("0.5")

    # Continuous counting categories: every calendar day counts
    if category_code in ("EL", "COL", "VL"):
        total_calendar_days = (end_date - start_date).days + 1
        return Decimal(total_calendar_days)

    # Working-day categories: skip weekends (Sat=5, Sun=6) and holidays
    holiday_set = holidays or set()
    working_days = 0
    cur = start_date
    one_day = timedelta(days=1)
    while cur <= end_date:
        if cur.weekday() < 5 and cur not in holiday_set:
            working_days += 1
        cur += one_day

    if working_days == 0:
        raise InvalidLeaveDateError(
            "Selected period contains no working days or falls entirely on holidays."
        )

    return Decimal(working_days)


def is_overlapping(
    new_start: date,
    new_end: date,
    new_half_day: str,
    existing_intervals: list[LeaveInterval],
) -> bool:
    """Check if the requested period overlaps with any existing leave interval.

    Rule: First-half and second-half CL on the same date do not overlap.
    """
    for ex in existing_intervals:
        # Check date intersection
        if max(new_start, ex.start_date) <= min(new_end, ex.end_date):
            # Special case: exactly same single date with complementary half-days
            if (
                new_start == new_end == ex.start_date == ex.end_date
                and new_half_day in ("first_half", "second_half")
                and ex.half_day in ("first_half", "second_half")
                and new_half_day != ex.half_day
            ):
                continue
            return True
    return False


def validate_leave_application(
    category_code: str,
    start_date: date,
    end_date: date,
    half_day: str,
    is_faculty: bool,
    current_balance: Decimal,
    pending_days: Decimal,
    station_leave: bool,
    station_address: str,
    emergency_contact: str,
    substitute_id: int | None,
    applicant_id: int,
    holidays: set[date] | None = None,
) -> Decimal:
    """Validate full leave application requirements and return computed days."""
    if category_code == "VL" and not is_faculty:
        raise IneligibleCategoryError(
            "Vacation Leave (VL) is restricted to faculty employees."
        )

    if station_leave:
        if not (station_address and station_address.strip()):
            raise StationLeaveValidationError(
                "Station address is required when station leave is requested."
            )
        if not (emergency_contact and emergency_contact.strip()):
            raise StationLeaveValidationError(
                "Emergency contact number is required when station leave is requested."
            )

    if substitute_id is not None and substitute_id == applicant_id:
        raise InvalidSubstituteError("An applicant cannot nominate themselves as substitute.")

    requested_days = calculate_leave_days(
        category_code=category_code,
        start_date=start_date,
        end_date=end_date,
        half_day=half_day,
        holidays=holidays,
    )

    available = current_balance - pending_days
    if available < requested_days:
        raise InsufficientLeaveBalanceError(
            f"Insufficient leave balance: requested {requested_days} days, "
            f"but only {available} days available."
        )

    return requested_days
