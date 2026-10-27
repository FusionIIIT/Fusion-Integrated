from datetime import date, datetime
from decimal import Decimal

import pytest

from modules.elm.domain.leave_days import (
    InvalidHalfDay,
    InvalidLeaveDate,
    UnsupportedLeaveCategory,
    UnsupportedLeaveCountingRule,
    calculate_chargeable_days,
)


@pytest.mark.parametrize("leave_type", ("EL", "COL", "VL"))
def test_single_day_continuous_leave_is_one_day(leave_type):
    result = calculate_chargeable_days(date(2025, 10, 1), date(2025, 10, 1), leave_type)

    assert result == Decimal("1")
    assert isinstance(result, Decimal)


@pytest.mark.parametrize("leave_type", ("EL", "COL", "VL"))
def test_continuous_leave_counts_weekend_days(leave_type):
    # Friday through Monday includes both intervening weekend dates.
    result = calculate_chargeable_days(date(2025, 10, 3), date(2025, 10, 6), leave_type)

    assert result == Decimal("4")


def test_continuous_leave_counts_a_closed_holiday_date():
    # The inclusive date span includes 2 October (a closed holiday date).
    result = calculate_chargeable_days(date(2025, 10, 2), date(2025, 10, 4), "EL")

    assert result == Decimal("3")


@pytest.mark.parametrize(
    ("start_date", "end_date"),
    (
        (date(2025, 1, 31), date(2025, 2, 2)),
        (date(2024, 12, 31), date(2025, 1, 2)),
    ),
)
def test_continuous_leave_counts_across_month_and_year_boundaries(start_date, end_date):
    assert calculate_chargeable_days(start_date, end_date, "COL") == Decimal("3")


@pytest.mark.parametrize("half_day", ("FIRST", "SECOND"))
def test_same_day_cl_half_day_consumes_exactly_half_a_day(half_day):
    result = calculate_chargeable_days(
        date(2025, 10, 1), date(2025, 10, 1), "CL", half_day=half_day
    )

    assert result == Decimal("0.5")
    assert isinstance(result, Decimal)


def test_cl_full_day_counting_is_explicitly_unsupported():
    with pytest.raises(UnsupportedLeaveCountingRule):
        calculate_chargeable_days(date(2025, 10, 1), date(2025, 10, 1), "CL")


def test_multi_day_cl_half_day_is_explicitly_unsupported():
    with pytest.raises(UnsupportedLeaveCountingRule):
        calculate_chargeable_days(date(2025, 10, 1), date(2025, 10, 2), "CL", half_day="FIRST")


@pytest.mark.parametrize("leave_type", ("RH", "SCL"))
def test_undefined_rh_and_scl_counting_is_explicitly_unsupported(leave_type):
    with pytest.raises(UnsupportedLeaveCountingRule):
        calculate_chargeable_days(date(2025, 10, 1), date(2025, 10, 2), leave_type)


def test_unknown_leave_category_is_rejected():
    with pytest.raises(UnsupportedLeaveCategory):
        calculate_chargeable_days(date(2025, 10, 1), date(2025, 10, 1), "UNKNOWN")


@pytest.mark.parametrize(
    ("start_date", "end_date"),
    (
        ("2025-10-01", date(2025, 10, 2)),
        (datetime(2025, 10, 1), date(2025, 10, 2)),
        (date(2025, 10, 1), datetime(2025, 10, 2)),
        (date(2025, 10, 2), date(2025, 10, 1)),
    ),
)
def test_malformed_datetime_or_reversed_ranges_are_rejected(start_date, end_date):
    with pytest.raises(InvalidLeaveDate):
        calculate_chargeable_days(start_date, end_date, "EL")


def test_invalid_half_day_metadata_is_rejected():
    with pytest.raises(InvalidHalfDay):
        calculate_chargeable_days(date(2025, 10, 1), date(2025, 10, 1), "CL", half_day="THIRD")


@pytest.mark.parametrize("leave_type", ("EL", "COL", "VL"))
def test_half_day_metadata_is_not_applied_to_continuous_categories(leave_type):
    with pytest.raises(UnsupportedLeaveCountingRule):
        calculate_chargeable_days(
            date(2025, 10, 1), date(2025, 10, 1), leave_type, half_day="FIRST"
        )
