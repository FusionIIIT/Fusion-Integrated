"""Regression tests for deterministic ELM policy calculations."""
from datetime import date
from decimal import Decimal

import pytest

from modules.elm.services.policy import (
    LeaveInterval, PolicyValidationError, count_leave_days,
    intervals_overlap, year_end_outcome,
)


def test_continuous_leave_counts_weekends():
    assert count_leave_days("EL", date(2026, 10, 30), date(2026, 11, 2)) == Decimal("4")


def test_non_continuous_leave_excludes_weekends_and_holidays():
    assert count_leave_days("CL", date(2026, 10, 30), date(2026, 11, 2),
                            excluded_dates={date(2026, 11, 2)}) == Decimal("1")


def test_half_day_cl_counts_half():
    assert count_leave_days("CL", date(2026, 11, 2), date(2026, 11, 2),
                            start_half="first") == Decimal("0.5")


def test_half_day_is_not_supported_for_el():
    with pytest.raises(PolicyValidationError):
        count_leave_days("EL", date(2026, 11, 2), date(2026, 11, 2), start_half="first")


def test_opposite_cl_halves_do_not_overlap():
    first = LeaveInterval(date(2026, 11, 2), date(2026, 11, 2), "CL", "approved", "first")
    second = LeaveInterval(date(2026, 11, 2), date(2026, 11, 2), "CL", "pending", "second")
    assert not intervals_overlap(first, second)


@pytest.mark.parametrize(("kind", "balance", "action", "credit"), [
    ("CL", "2", "lapse", "0"), ("RH", "1", "lapse", "0"),
    ("SCL", "4", "lapse", "0"), ("EL", "8", "carry_forward", "0"),
    ("COL", "3", "carry_forward", "0"), ("VL", "5", "convert_to_el", "2.5"),
])
def test_year_end_policy(kind, balance, action, credit):
    result = year_end_outcome(kind, Decimal(balance))
    assert result["action"] == action
    assert result["credited_el"] == Decimal(credit)


def test_invalid_date_range_is_rejected():
    with pytest.raises(PolicyValidationError):
        count_leave_days("CL", date(2026, 11, 3), date(2026, 11, 2))
