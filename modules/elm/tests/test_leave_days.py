from datetime import date
from decimal import Decimal

import pytest

from modules.elm.domain.leave_days import count_leave_days


def test_single_working_day():
    assert count_leave_days(date(2026, 11, 2), date(2026, 11, 2)) == Decimal("1")


def test_monday_to_wednesday_is_three_days():
    assert count_leave_days(date(2026, 11, 2), date(2026, 11, 4)) == Decimal("3")


def test_weekend_days_are_not_counted():
    # Fri 6 Nov to Tue 10 Nov: Fri, Mon, Tue
    assert count_leave_days(date(2026, 11, 6), date(2026, 11, 10)) == Decimal("3")


def test_half_day_counts_as_half():
    assert count_leave_days(
        date(2026, 11, 2), date(2026, 11, 2), "first_half"
    ) == Decimal("0.5")


def test_half_day_over_two_days_is_rejected():
    with pytest.raises(ValueError):
        count_leave_days(date(2026, 11, 2), date(2026, 11, 3), "first_half")


def test_end_before_start_is_rejected():
    with pytest.raises(ValueError):
        count_leave_days(date(2026, 11, 4), date(2026, 11, 2))
