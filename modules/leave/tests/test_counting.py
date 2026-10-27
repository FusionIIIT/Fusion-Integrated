"""Unit tests for leave-day calculation (BR-EL-010, BR-EL-011)."""
import datetime
from decimal import Decimal
import pytest

from core.api.exceptions import BadRequestError
from modules.leave.domain.counting import calculate_leave_days


def test_cl_half_day():
    d = datetime.date(2026, 10, 12)  # Monday
    assert calculate_leave_days("CL", d, d, half_day_type="first_half") == Decimal("0.5")
    assert calculate_leave_days("CL", d, d, half_day_type="second_half") == Decimal("0.5")


def test_half_day_not_allowed_for_el():
    d = datetime.date(2026, 10, 12)
    with pytest.raises(BadRequestError):
        calculate_leave_days("EL", d, d, half_day_type="first_half")


def test_continuous_counting_for_el_includes_weekends():
    # Friday to Monday = 4 continuous days
    start = datetime.date(2026, 10, 16)  # Friday
    end = datetime.date(2026, 10, 19)    # Monday
    days = calculate_leave_days("EL", start, end)
    assert days == Decimal("4.0")


def test_working_days_counting_for_cl_excludes_weekends():
    # Friday to Monday = only Friday and Monday (2 working days)
    start = datetime.date(2026, 10, 16)  # Friday
    end = datetime.date(2026, 10, 19)    # Monday
    days = calculate_leave_days("CL", start, end)
    assert days == Decimal("2.0")


def test_rh_must_match_calendar():
    rh_date = datetime.date(2026, 10, 20)
    # Valid RH date
    days = calculate_leave_days("RH", rh_date, rh_date, rh_holidays={rh_date})
    assert days == Decimal("1.0")

    # Invalid non-RH date
    with pytest.raises(BadRequestError):
        calculate_leave_days("RH", rh_date, rh_date, rh_holidays=set())
