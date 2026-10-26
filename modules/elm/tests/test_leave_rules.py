from datetime import date
from decimal import Decimal

import pytest

from modules.elm.domain.leave_rules import (
    can_review,
    count_leave_days,
    has_enough_balance,
)


def test_single_full_day():
    assert count_leave_days(date(2026, 11, 2), date(2026, 11, 2), "full") == Decimal("1")


def test_multi_day_is_inclusive():
    assert count_leave_days(date(2026, 11, 2), date(2026, 11, 4), "full") == Decimal("3")


def test_half_day_counts_as_half():
    assert count_leave_days(date(2026, 11, 2), date(2026, 11, 2), "first_half") == Decimal("0.5")


def test_half_day_over_several_days_is_invalid():
    with pytest.raises(ValueError):
        count_leave_days(date(2026, 11, 2), date(2026, 11, 3), "second_half")


def test_end_before_start_is_invalid():
    with pytest.raises(ValueError):
        count_leave_days(date(2026, 11, 5), date(2026, 11, 2), "full")


def test_enough_balance():
    assert has_enough_balance(Decimal("5"), Decimal("5")) is True
    assert has_enough_balance(Decimal("4.5"), Decimal("5")) is False


def test_cannot_review_own_request():
    assert can_review(reviewer_id=7, applicant_id=7) is False
    assert can_review(reviewer_id=7, applicant_id=8) is True
