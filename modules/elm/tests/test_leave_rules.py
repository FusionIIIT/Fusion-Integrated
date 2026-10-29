from datetime import date
from decimal import Decimal

import pytest

from modules.elm.domain.leave_rules import (
    HolidayCalendar,
    LeaveCategory,
    MissingLeaveFactsError,
    UnresolvedLeavePolicyError,
    VacationPeriod,
    calculate_chargeable_days,
    convert_unused_faculty_vl_to_el,
    validate_faculty_vl_period,
    validate_rh_date,
)


def test_cl_counts_weekdays_and_excludes_closed_holidays():
    result = calculate_chargeable_days(
        date(2024, 1, 1),
        date(2024, 1, 5),
        LeaveCategory.CL,
        [date(2024, 1, 1)],
    )
    assert result == Decimal("4")


def test_cl_weekend_only_range_counts_zero():
    result = calculate_chargeable_days(
        date(2024, 1, 6),
        date(2024, 1, 7),
        LeaveCategory.CL,
        [],
    )
    assert result == Decimal("0")


def test_cl_requires_closed_holiday_data():
    with pytest.raises(MissingLeaveFactsError):
        calculate_chargeable_days(
            date(2024, 1, 1), date(2024, 1, 2),
            LeaveCategory.CL, None
        )


@pytest.mark.parametrize("category", [LeaveCategory.EL, LeaveCategory.VL])
def test_el_and_vl_count_both_endpoints(category):
    result = calculate_chargeable_days(
        date(2024, 2, 28), date(2024, 3, 1), category, []
    )
    assert result == Decimal("3")


def test_reversed_date_range_is_rejected():
    with pytest.raises(ValueError, match="Reversed"):
        calculate_chargeable_days(
            date(2024, 1, 2), date(2024, 1, 1),
            LeaveCategory.EL, []
        )


def test_col_policy_remains_unresolved():
    with pytest.raises(UnresolvedLeavePolicyError):
        calculate_chargeable_days(
            date(2024, 1, 1), date(2024, 1, 2),
            LeaveCategory.COL, []
        )


def test_rh_requires_published_effective_calendar():
    calendar = HolidayCalendar(
        holidays=[date(2024, 1, 26)],
        published=True,
        effective_from=date(2024, 1, 1),
        effective_to=date(2024, 12, 31),
    )
    validate_rh_date(date(2024, 1, 26), calendar)


def test_rh_rejects_date_not_in_calendar():
    calendar = HolidayCalendar(
        holidays=[date(2024, 1, 26)],
        published=True,
        effective_from=date(2024, 1, 1),
        effective_to=date(2024, 12, 31),
    )
    with pytest.raises(ValueError):
        validate_rh_date(date(2024, 1, 27), calendar)


def test_faculty_vl_must_fit_vacation_period():
    periods = [VacationPeriod(date(2024, 5, 1), date(2024, 6, 30))]
    validate_faculty_vl_period(
        date(2024, 5, 10), date(2024, 5, 20), "faculty", periods
    )
    with pytest.raises(ValueError):
        validate_faculty_vl_period(
            date(2024, 4, 29), date(2024, 5, 5), "faculty", periods
        )


def test_unused_faculty_vl_converts_at_two_to_one():
    assert convert_unused_faculty_vl_to_el(Decimal("7.5")) == Decimal("3.75")


def test_negative_unused_vl_is_rejected():
    with pytest.raises(ValueError):
        convert_unused_faculty_vl_to_el(Decimal("-1"))


def test_invalid_category_is_rejected():
    with pytest.raises(ValueError, match="Invalid leave category"):
        calculate_chargeable_days(
            date(2024, 1, 1), date(2024, 1, 2), "CL", []
        )


def test_missing_rh_calendar_is_rejected():
    with pytest.raises(MissingLeaveFactsError, match="calendar is missing"):
        validate_rh_date(date(2024, 1, 26), None)


def test_unpublished_rh_calendar_is_rejected():
    calendar = HolidayCalendar(
        holidays=[date(2024, 1, 26)],
        published=False,
        effective_from=date(2024, 1, 1),
        effective_to=date(2024, 12, 31),
    )
    with pytest.raises(MissingLeaveFactsError, match="not published"):
        validate_rh_date(date(2024, 1, 26), calendar)


def test_faculty_vl_requires_vacation_periods():
    with pytest.raises(MissingLeaveFactsError, match="calendar is missing"):
        validate_faculty_vl_period(
            date(2024, 5, 10), date(2024, 5, 20), "faculty", None
        )


def test_faculty_vl_rejects_non_faculty_classification():
    with pytest.raises(ValueError, match="applies to faculty"):
        validate_faculty_vl_period(
            date(2024, 5, 10),
            date(2024, 5, 20),
            "staff",
            [VacationPeriod(date(2024, 5, 1), date(2024, 6, 30))],
        )
