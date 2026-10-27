from datetime import date
from decimal import Decimal

import pytest

from modules.elm.domain import rules


@pytest.mark.parametrize(
    "category,expected", [("CL", "1"), ("SCL", "1"), ("EL", "4"), ("COL", "4"), ("VL", "4")]
)
def test_continuous_leave_counts_weekend_and_holiday(category, expected):
    calendar = {2026: {"holidays": ["2026-12-25"], "restricted_holidays": []}}
    assert rules.count_days(
        category, date(2026, 12, 24), date(2026, 12, 27), "full", calendar, [5, 6]
    ) == {2026: Decimal(expected)}


@pytest.mark.parametrize("half", ["first", "second"])
def test_half_day_cl_consumes_half(half):
    calendar = {2026: {"holidays": [], "restricted_holidays": []}}
    assert rules.count_days("CL", date(2026, 11, 2), date(2026, 11, 2), half, calendar, [5, 6]) == {
        2026: Decimal("0.5")
    }


def test_invalid_day_portion_is_not_silently_a_half_day():
    with pytest.raises(rules.RuleViolation, match=r"portion|half"):
        rules.count_days(
            "CL",
            date(2026, 11, 2),
            date(2026, 11, 2),
            "invalid",
            {2026: {"holidays": [], "restricted_holidays": []}},
            [5, 6],
        )


def test_opposite_halves_are_disjoint_but_full_day_overlaps():
    day = date(2026, 11, 2)
    assert not rules.overlaps(day, day, "first", day, day, "second")
    assert rules.overlaps(day, day, "first", day, day, "full")


def test_calendar_missing_and_invalid_rh_fail_closed():
    with pytest.raises(rules.RuleViolation) as missing:
        rules.count_days("EL", date(2026, 12, 31), date(2027, 1, 1), "full", {}, [])
    assert missing.value.code == "calendar_missing"
    with pytest.raises(rules.RuleViolation) as rh:
        rules.count_days(
            "RH",
            date(2026, 11, 2),
            date(2026, 11, 2),
            "full",
            {2026: {"holidays": [], "restricted_holidays": []}},
            [],
        )
    assert rh.value.code == "invalid_rh"


def test_cross_year_charge_is_split():
    calendars = {year: {"holidays": [], "restricted_holidays": []} for year in (2026, 2027)}
    assert rules.count_days("EL", date(2026, 12, 31), date(2027, 1, 2), "full", calendars, []) == {
        2026: Decimal("1"),
        2027: Decimal("2"),
    }
