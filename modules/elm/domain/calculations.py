"""Pure Python business calculations for ELM.

Encapsulates leave-day counting rules, half-day CL calculations,
VL-to-EL conversions, and overlap validations.
Zero framework dependencies.
"""
from __future__ import annotations

from collections.abc import Set
from datetime import date, timedelta

from modules.elm.domain.entities import LeaveCategory, LeaveValidationResult


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
    - BR-EL-011: Continuous counting for EL, VL, COL includes weekends & holidays.
    - BR-EL-011: CL, SCL, RH exclude weekends (Saturday, Sunday) and closed holidays.
    """
    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date.")

    cat_str = category.value if isinstance(category, LeaveCategory) else str(category)

    # Half-day Casual Leave rule (BR-EL-010)
    if cat_str == LeaveCategory.CL.value and is_half_day:
        if start_date != end_date:
            raise ValueError("Half-day CL must have identical start and end dates.")
        return 0.5

    # Continuous counting for EL, VL, COL (BR-EL-011)
    if cat_str in (LeaveCategory.EL.value, LeaveCategory.VL.value, LeaveCategory.COL.value):
        total_calendar_days = (end_date - start_date).days + 1
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
    if unused_vl < 0:
        return 0.0
    return round(unused_vl / 2.0, 2)


def check_date_overlap(
    start1: date,
    end1: date,
    is_half1: bool,
    period1: str | None,
    start2: date,
    end2: date,
    is_half2: bool,
    period2: str | None,
) -> bool:
    """Check if two leave periods conflict.

    Rule BR-EL-012: First-half and second-half CL on the same date do not overlap.
    """
    # If entirely distinct dates, no overlap
    if end1 < start2 or end2 < start1:
        return False

    # Single-date half-day exception
    if start1 == end1 == start2 == end2:
        if is_half1 and is_half2:
            # Different half-days (first_half vs second_half) do NOT overlap
            if period1 and period2 and period1 != period2:
                return False

    return True


def validate_leave_application(
    category: str,
    start_date: date,
    end_date: date,
    available_balance: float,
    is_half_day: bool = False,
    half_day_period: str | None = None,
    closed_holidays: Set[date] | None = None,
    is_faculty: bool = True,
    vacation_periods: list[tuple[date, date]] | None = None,
    published_rh_dates: Set[date] | None = None,
) -> LeaveValidationResult:
    """Validate leave eligibility, calendar constraints, and balance (BR-EL-001 - BR-EL-006)."""
    if start_date > end_date:
        return LeaveValidationResult(False, 0.0, "Start date cannot be after end date.")

    # Faculty Vacation Leave constraint (BR-EL-006)
    if category == LeaveCategory.VL.value:
        if not is_faculty:
            return LeaveValidationResult(False, 0.0, "Vacation Leave is only available to faculty.")
        # Must fall within published academic vacation period
        vac_periods = vacation_periods or []
        falls_in_vacation = any(v_start <= start_date and end_date <= v_end
                                for v_start, v_end in vac_periods)
        if not falls_in_vacation:
            return LeaveValidationResult(
                False, 0.0, "Vacation Leave must fall entirely within a published vacation period."
            )

    # Restricted Holiday calendar constraint (BR-EL-003)
    if category == LeaveCategory.RH.value:
        rh_dates = published_rh_dates or set()
        if start_date not in rh_dates or end_date not in rh_dates:
            return LeaveValidationResult(
                False, 0.0, "Restricted Holiday request must match published RH calendar dates."
            )

    # Calculate net days
    try:
        needed_days = calculate_leave_days(
            category=category,
            start_date=start_date,
            end_date=end_date,
            is_half_day=is_half_day,
            half_day_period=half_day_period,
            closed_holidays=closed_holidays,
        )
    except ValueError as e:
        return LeaveValidationResult(False, 0.0, str(e))

    if needed_days <= 0:
        return LeaveValidationResult(False, 0.0, "Requested leave period results in 0 valid leave days.")

    # Balance check
    if needed_days > available_balance:
        return LeaveValidationResult(
            False, needed_days,
            f"Insufficient leave balance. Requested: {needed_days}, Available: {available_balance}."
        )

    return LeaveValidationResult(True, needed_days)
