"""Fast pure-domain tests (run with pytest modules/elm/domain/test_counting.py)."""

from datetime import date
from decimal import Decimal

import pytest

from modules.elm.domain.counting import chargeable_days, intervals_overlap
from modules.elm.domain.errors import InvalidLeaveRequest


def test_continuous_leave_counts_weekends():
    assert chargeable_days("EL", date(2026, 10, 30), date(2026, 11, 2)) == Decimal("4")


def test_restricted_holiday_counts_as_one_leave_day():
    assert chargeable_days(
        "RH", date(2026, 10, 31), date(2026, 10, 31), closed_dates={date(2026, 10, 31)}
    ) == Decimal("1")


def test_cl_excludes_published_closed_weekday():
    assert chargeable_days(
        "CL", date(2026, 10, 26), date(2026, 10, 27), closed_dates={date(2026, 10, 27)}
    ) == Decimal("1")


def test_half_day_cl_is_half():
    assert chargeable_days(
        "CL", date(2026, 10, 28), date(2026, 10, 28), half_day="first"
    ) == Decimal("0.5")


def test_half_day_only_for_single_day_cl():
    with pytest.raises(InvalidLeaveRequest):
        chargeable_days("EL", date(2026, 10, 28), date(2026, 10, 28), half_day="first")


def test_interval_overlap_inclusive():
    assert intervals_overlap(date(2026, 1, 1), date(2026, 1, 3), date(2026, 1, 3), date(2026, 1, 4))
