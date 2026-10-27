"""Pure domain policy functions for Employee Leave Management.

Enforces business rules BR-EL-001 through BR-EL-038 with no database or framework dependencies.
"""
from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Collection, Iterable, Optional, Sequence, Tuple

from .errors import (
    CalendarValidationError,
    EligibilityError,
    ELMValidationError,
    OverlapError,
)

# Standard entitlements per academic/calendar year
ANNUAL_ENTITLEMENTS = {
    "CL": Decimal("8.0"),     # BR-EL-002
    "RH": Decimal("2.0"),     # BR-EL-003
    "SCL": Decimal("15.0"),   # BR-EL-004
    "EL_STAFF": Decimal("30.0"),  # BR-EL-005
    "VL_FACULTY": Decimal("60.0"),  # BR-EL-006
    "COL": Decimal("20.0"),   # BR-EL-009
}

CONTINUOUS_COUNT_CATEGORIES = frozenset({"EL", "COL", "VL"})
WORKING_DAYS_CATEGORIES = frozenset({"CL", "SCL", "RH"})


def validate_eligibility(employee_kind: str, category: str) -> None:
    """Validate whether an employee category can apply for the leave category (BR-EL-001)."""
    kind = employee_kind.lower()
    cat = category.upper()

    if cat not in {"CL", "RH", "SCL", "EL", "VL", "COL"}:
        raise EligibilityError(f"Unsupported leave category '{category}'.")

    if kind == "faculty":
        # Faculty primary vacation leave is VL (BR-EL-006). They can hold converted EL (BR-EL-008).
        if cat == "EL":
            # Permitted if the faculty has balance resulting from VL conversion.
            pass
    elif kind == "staff":
        # Staff cannot avail Vacation Leave (VL is faculty only).
        if cat == "VL":
            raise EligibilityError("Vacation Leave (VL) is restricted to Faculty members.")
    else:
        raise EligibilityError(f"Unknown employee kind '{employee_kind}'.")


def calculate_leave_duration(
    category: str,
    start_date: datetime.date,
    end_date: datetime.date,
    is_half_day: bool = False,
    half_day_type: Optional[str] = None,
    holiday_calendar: Optional[Collection[datetime.date]] = None,
) -> Decimal:
    """Calculate the billable leave duration in days according to category counting rules.
    
    - Half-day CL is 0.5 days (BR-EL-010).
    - EL, COL, and VL use continuous-day counting (including weekends and holidays) (BR-EL-011).
    - CL, SCL, and RH exclude weekends and closed holidays (BR-EL-011).
    """
    if start_date > end_date:
        raise ELMValidationError("Start date cannot be after end date.")

    cat = category.upper()

    if is_half_day:
        if cat != "CL":
            raise ELMValidationError("Half-day leave is only supported for Casual Leave (CL).")
        if start_date != end_date:
            raise ELMValidationError("Half-day leave must be on a single date.")
        if half_day_type not in ("first_half", "second_half"):
            raise ELMValidationError("half_day_type must be 'first_half' or 'second_half'.")
        return Decimal("0.5")

    # Continuous counting for EL, COL, VL
    if cat in CONTINUOUS_COUNT_CATEGORIES:
        return Decimal(str((end_date - start_date).days + 1))

    # Working day counting for CL, SCL, RH
    holidays = holiday_calendar or set()
    total_days = Decimal("0.0")
    curr = start_date
    one_day = datetime.timedelta(days=1)

    while curr <= end_date:
        # 5 = Saturday, 6 = Sunday
        if curr.weekday() not in (5, 6) and curr not in holidays:
            total_days += Decimal("1.0")
        curr += one_day

    return total_days


def validate_rh_calendar(
    req_date: datetime.date,
    published_rh_dates: Collection[datetime.date],
) -> None:
    """Ensure requested Restricted Holiday matches an officially published RH date (BR-EL-003, BR-EL-031)."""
    if req_date not in published_rh_dates:
        raise CalendarValidationError(
            f"Date {req_date.isoformat()} is not listed in the published Restricted Holiday calendar."
        )


def validate_vl_vacation_window(
    start_date: datetime.date,
    end_date: datetime.date,
    vacation_windows: Sequence[Tuple[datetime.date, datetime.date]],
) -> None:
    """Ensure VL interval falls strictly within an Academic Calendar vacation period (BR-EL-006)."""
    for v_start, v_end in vacation_windows:
        if v_start <= start_date and end_date <= v_end:
            return

    raise CalendarValidationError(
        f"Requested VL period {start_date} to {end_date} does not fall within any published Academic Calendar vacation period."
    )


def check_date_overlap(
    start_1: datetime.date,
    end_1: datetime.date,
    half_1: Optional[str],
    start_2: datetime.date,
    end_2: datetime.date,
    half_2: Optional[str],
) -> bool:
    """Determine whether two leave intervals impermissibly overlap (BR-EL-012).
    
    Exception: Non-overlapping half-day CL on the exact same date (first_half vs second_half).
    """
    if end_1 < start_2 or end_2 < start_1:
        return False

    # Check if they intersect on the exact same single day with complementary halves
    if start_1 == end_1 == start_2 == end_2:
        if half_1 in ("first_half", "second_half") and half_2 in ("first_half", "second_half"):
            if half_1 != half_2:
                return False

    return True


def convert_vl_to_el(unused_vl: Decimal) -> Decimal:
    """Convert unused faculty VL to EL at 2 VL : 1 EL (BR-EL-007, BR-EL-008)."""
    if unused_vl < Decimal("0.0"):
        return Decimal("0.0")
    # Fractional conversion supported, e.g. 15 VL -> 7.5 EL
    return unused_vl / Decimal("2.0")


def calculate_resumption_adjustment(
    approved_start: datetime.date,
    approved_end: datetime.date,
    actual_resumption_date: datetime.date,
    category: str = "EL",
    holiday_calendar: Optional[Collection[datetime.date]] = None,
) -> Tuple[str, Decimal, Decimal]:
    """Calculate actual days taken and balance adjustment for early/normal/late resumption (BR-EL-028).
    
    Returns:
        (resumption_type, adjustment_delta, actual_days_taken)
        - adjustment_delta > 0 indicates days to credit back to employee balance.
        - adjustment_delta < 0 indicates excess days to deduct.
    """
    expected_resumption = approved_end + datetime.timedelta(days=1)
    approved_duration = calculate_leave_duration(
        category, approved_start, approved_end, holiday_calendar=holiday_calendar
    )

    if actual_resumption_date == expected_resumption:
        return ("NORMAL", Decimal("0.0"), approved_duration)

    if actual_resumption_date < expected_resumption:
        # Early resumption
        if actual_resumption_date <= approved_start:
            actual_days = Decimal("0.0")
        else:
            actual_end = actual_resumption_date - datetime.timedelta(days=1)
            actual_days = calculate_leave_duration(
                category, approved_start, actual_end, holiday_calendar=holiday_calendar
            )
        credit_back = approved_duration - actual_days
        return ("EARLY", credit_back, actual_days)

    # Late resumption
    excess_start = expected_resumption
    excess_end = actual_resumption_date - datetime.timedelta(days=1)
    excess_days = calculate_leave_duration(
        category, excess_start, excess_end, holiday_calendar=holiday_calendar
    )
    total_taken = approved_duration + excess_days
    return ("LATE", -excess_days, total_taken)
