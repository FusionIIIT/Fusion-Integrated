# Tests for leave counting calculations (BR-EL-010, BR-EL-011)
from datetime import date
from decimal import Decimal

import pytest

from core.api.exceptions import BadRequestError
from modules.leave.domain.calculations import calculate_leave_days
from modules.leave.domain.constants import (
    HALF_DAY_FIRST,
    HALF_DAY_NONE,
    HALF_DAY_SECOND,
    LEAVE_TYPE_CL,
    LEAVE_TYPE_COL,
    LEAVE_TYPE_EL,
    LEAVE_TYPE_RH,
    LEAVE_TYPE_SCL,
    LEAVE_TYPE_VL,
)


def test_half_day_casual_leave():
    """BR-EL-010: Half-day CL deducts exactly 0.5 days."""
    single_date = date(2026, 11, 4)  # Wednesday
    days_first = calculate_leave_days(LEAVE_TYPE_CL, single_date, single_date, HALF_DAY_FIRST)
    days_second = calculate_leave_days(LEAVE_TYPE_CL, single_date, single_date, HALF_DAY_SECOND)

    assert days_first == Decimal("0.5")
    assert days_second == Decimal("0.5")


def test_half_day_prohibited_for_non_cl():
    """BR-EL-010: Half-day is strictly restricted to Casual Leave."""
    single_date = date(2026, 11, 4)
    with pytest.raises(BadRequestError, match="only permitted for Casual Leave"):
        calculate_leave_days(LEAVE_TYPE_EL, single_date, single_date, HALF_DAY_FIRST)

    with pytest.raises(BadRequestError, match="only permitted for Casual Leave"):
        calculate_leave_days(LEAVE_TYPE_SCL, single_date, single_date, HALF_DAY_SECOND)


def test_half_day_requires_identical_dates():
    """BR-EL-010: Half-day cannot span multiple dates."""
    start = date(2026, 11, 4)
    end = date(2026, 11, 5)
    with pytest.raises(BadRequestError, match="identical start and end dates"):
        calculate_leave_days(LEAVE_TYPE_CL, start, end, HALF_DAY_FIRST)


def test_continuous_day_counting():
    """BR-EL-011: EL, COL, VL count continuous calendar days including weekends."""
    # Friday 2026-11-06 to Monday 2026-11-09 (4 calendar days)
    start = date(2026, 11, 6)  # Friday
    end = date(2026, 11, 9)    # Monday

    assert calculate_leave_days(LEAVE_TYPE_EL, start, end, HALF_DAY_NONE) == Decimal("4")
    assert calculate_leave_days(LEAVE_TYPE_COL, start, end, HALF_DAY_NONE) == Decimal("4")
    assert calculate_leave_days(LEAVE_TYPE_VL, start, end, HALF_DAY_NONE) == Decimal("4")


def test_working_day_counting_excludes_weekends():
    """BR-EL-011: CL, SCL, RH exclude weekends (Saturday and Sunday)."""
    # Friday 2026-11-06 to Monday 2026-11-09 (Fri + Mon = 2 working days)
    start = date(2026, 11, 6)
    end = date(2026, 11, 9)

    assert calculate_leave_days(LEAVE_TYPE_CL, start, end, HALF_DAY_NONE) == Decimal("2")
    assert calculate_leave_days(LEAVE_TYPE_SCL, start, end, HALF_DAY_NONE) == Decimal("2")
    assert calculate_leave_days(LEAVE_TYPE_RH, start, end, HALF_DAY_NONE) == Decimal("2")


def test_invalid_date_range():
    """End date prior to start date must raise BadRequestError."""
    start = date(2026, 11, 10)
    end = date(2026, 11, 8)
    with pytest.raises(BadRequestError, match="End date cannot be prior"):
        calculate_leave_days(LEAVE_TYPE_CL, start, end)


def test_weekend_only_dates_for_working_leave():
    """Selecting only Saturday and Sunday for CL raises BadRequestError."""
    sat = date(2026, 11, 7)
    sun = date(2026, 11, 8)
    with pytest.raises(BadRequestError, match="only cover non-working weekend days"):
        calculate_leave_days(LEAVE_TYPE_CL, sat, sun)
