"""Unit tests for the pure Python domain layer of Leave Management."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from modules.leave.domain.counting import calculate_leave_days
from modules.leave.domain.entities import HalfDayType, LeaveCategory, LeaveStatus
from modules.leave.domain.errors import (
    IneligibleSubstituteError,
    InvalidDateRangeError,
    InvalidStateTransitionError,
    OverlappingLeaveError,
    RestrictedHolidayMismatchError,
    VacationCalendarMismatchError,
)
from modules.leave.domain.rules import (
    calculate_resumption_adjustment,
    calculate_year_end_conversions,
    validate_cancellation_allowed,
    validate_category_eligibility,
    validate_no_overlap,
    validate_positive_leave_days,
    validate_resumption_allowed,
    validate_rh_date,
    validate_substitute_eligibility,
    validate_vacation_period,
)


def test_continuous_counting_includes_weekends_and_holidays():
    """BR-EL-012: For EL, COL, VL, intervening weekends & holidays count as leave days."""
    start = date(2026, 10, 5)
    end = date(2026, 10, 14)
    days = calculate_leave_days(LeaveCategory.EL.value, start, end)
    assert days == Decimal("10.0")

    days_col = calculate_leave_days(LeaveCategory.COL.value, start, end)
    assert days_col == Decimal("10.0")

    days_vl = calculate_leave_days(LeaveCategory.VL.value, start, end)
    assert days_vl == Decimal("10.0")


def test_working_day_counting_excludes_weekends_and_closed_holidays():
    """BR-EL-012: For CL, SCL, RH, intervening weekends and closed holidays do NOT count."""
    start = date(2026, 10, 5)
    end = date(2026, 10, 11)
    closed_holidays = {date(2026, 10, 7)}

    days = calculate_leave_days(
        LeaveCategory.CL.value,
        start,
        end,
        closed_holiday_dates=closed_holidays,
    )
    assert days == Decimal("4.0")


def test_half_day_cl_counts_as_half():
    """BR-EL-011: CL supports first-half and second-half consuming 0.5 days."""
    d = date(2026, 10, 5)
    days_fh = calculate_leave_days(
        LeaveCategory.CL.value, d, d, half_day_type=HalfDayType.FIRST_HALF.value
    )
    assert days_fh == Decimal("0.5")

    days_sh = calculate_leave_days(
        LeaveCategory.CL.value, d, d, half_day_type=HalfDayType.SECOND_HALF.value
    )
    assert days_sh == Decimal("0.5")

    with pytest.raises(InvalidDateRangeError):
        calculate_leave_days(
            LeaveCategory.CL.value,
            d,
            d + timedelta(days=1),
            half_day_type=HalfDayType.FIRST_HALF.value,
        )


def test_category_eligibility():
    """Staff cannot avail VL directly."""
    with pytest.raises(InvalidStateTransitionError):
        validate_category_eligibility("staff", LeaveCategory.VL.value)
    validate_category_eligibility("faculty", LeaveCategory.VL.value)


def test_rh_date_validation():
    """BR-EL-003: RH request must match a date in published RH calendar and be a single day."""
    rh_dates = {date(2026, 10, 20), date(2026, 11, 15)}
    # Single valid day: passes
    validate_rh_date(date(2026, 10, 20), date(2026, 10, 20), rh_dates)

    # Date not in calendar: fails
    with pytest.raises(RestrictedHolidayMismatchError):
        validate_rh_date(date(2026, 10, 21), date(2026, 10, 21), rh_dates)

    # Multi-day RH: fails
    with pytest.raises(RestrictedHolidayMismatchError):
        validate_rh_date(date(2026, 10, 20), date(2026, 10, 21), rh_dates)


def test_positive_leave_days_validation():
    """BR-EL-011: Zero or negative days leave must be rejected."""
    validate_positive_leave_days(Decimal("0.5"))
    validate_positive_leave_days(Decimal("1.0"))

    with pytest.raises(InvalidDateRangeError):
        validate_positive_leave_days(Decimal("0.0"))


def test_vacation_period_validation():
    """BR-EL-006: VL must fall within an academic vacation period."""
    vacations = [(date(2026, 6, 1), date(2026, 7, 15))]
    validate_vacation_period(date(2026, 6, 10), date(2026, 6, 20), vacations)

    with pytest.raises(VacationCalendarMismatchError):
        validate_vacation_period(date(2026, 7, 10), date(2026, 7, 25), vacations)


def test_substitute_validation():
    """BR-EL-014: Substitute cannot be self or on active leave."""
    with pytest.raises(IneligibleSubstituteError):
        validate_substitute_eligibility(
            applicant_user_id=1001,
            substitute_user_id=1001,
            substitute_active_leaves=[],
            requested_start=date(2026, 10, 1),
            requested_end=date(2026, 10, 5),
        )

    sub_leaves = [(date(2026, 10, 3), date(2026, 10, 8))]
    with pytest.raises(IneligibleSubstituteError):
        validate_substitute_eligibility(
            applicant_user_id=1001,
            substitute_user_id=1002,
            substitute_active_leaves=sub_leaves,
            requested_start=date(2026, 10, 1),
            requested_end=date(2026, 10, 5),
        )


def test_leave_overlap_and_half_day_exception():
    """BR-EL-012: Overlap is blocked except for opposite CL halves on same date."""
    existing = [
        {
            "start_date": date(2026, 10, 5),
            "end_date": date(2026, 10, 5),
            "leave_type": "CL",
            "half_day_type": "FIRST_HALF",
        }
    ]
    validate_no_overlap(existing, date(2026, 10, 5), date(2026, 10, 5), "CL", "SECOND_HALF")

    with pytest.raises(OverlappingLeaveError):
        validate_no_overlap(existing, date(2026, 10, 5), date(2026, 10, 5), "CL", "FIRST_HALF")

    with pytest.raises(OverlappingLeaveError):
        validate_no_overlap(existing, date(2026, 10, 5), date(2026, 10, 7), "EL", "FULL")


def test_cancellation_allowed():
    """BR-EL-023: Cancellation allowed only before leave begins."""
    start = date(2026, 10, 10)
    validate_cancellation_allowed(LeaveStatus.APPROVED.value, start, date(2026, 10, 8))

    with pytest.raises(InvalidStateTransitionError):
        validate_cancellation_allowed(LeaveStatus.APPROVED.value, start, date(2026, 10, 10))


def test_resumption_allowed_validation():
    """BR-EL-027: Resumption date cannot be earlier than leave start date."""
    start = date(2026, 10, 5)
    validate_resumption_allowed(start, date(2026, 10, 8))

    with pytest.raises(InvalidStateTransitionError):
        validate_resumption_allowed(start, date(2026, 10, 4))


def test_resumption_adjustment_calculation():
    """BR-EL-028: Resumption adjustments."""
    app_start = date(2026, 10, 1)
    app_end = date(2026, 10, 10)

    adj_normal = calculate_resumption_adjustment(app_start, app_end, app_end, "EL")
    assert adj_normal == Decimal("0.0")

    adj_early = calculate_resumption_adjustment(app_start, app_end, date(2026, 10, 8), "EL")
    assert adj_early == Decimal("-2.0")

    adj_late = calculate_resumption_adjustment(app_start, app_end, date(2026, 10, 12), "EL")
    assert adj_late == Decimal("2.0")


def test_year_end_conversions():
    """BR-EL-002, BR-EL-003, BR-EL-007, BR-EL-008: Year end conversions."""
    balances = {
        "CL": Decimal("3.0"),
        "RH": Decimal("1.0"),
        "SCL": Decimal("5.0"),
        "EL": Decimal("10.0"),
        "VL": Decimal("30.0"),
        "COL": Decimal("15.0"),
    }
    new_bal, vl_to_el = calculate_year_end_conversions(balances, is_faculty=True)
    assert new_bal["CL"] == Decimal("0.0")
    assert new_bal["RH"] == Decimal("0.0")
    assert new_bal["SCL"] == Decimal("0.0")
    assert vl_to_el == Decimal("15.0")
    assert new_bal["EL"] == Decimal("25.0")
    assert new_bal["VL"] == Decimal("0.0")
