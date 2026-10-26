"""Focused tests for ELM's pure leave-policy functions."""

from datetime import date
from decimal import Decimal

import pytest

from modules.elm.domain.policy import chargeable_days, overlaps, split_days_by_year


def test_continuous_leave_counts_weekends_and_closed_dates():
    assert chargeable_days(
        category="EL",
        start=date(2026, 1, 2),
        end=date(2026, 1, 5),
        counting_rule="continuous",
        closed_dates={date(2026, 1, 5)},
    ) == Decimal("4")


def test_noncontinuous_working_days_skip_weekends_and_closed_dates():
    assert chargeable_days(
        category="CL",
        start=date(2026, 1, 2),
        end=date(2026, 1, 6),
        counting_rule="working_days",
        closed_dates={date(2026, 1, 5)},
    ) == Decimal("2")


def test_half_day_cl_obeys_its_configured_counting_rule():
    assert chargeable_days(
        category="CL",
        start=date(2026, 1, 5),
        end=date(2026, 1, 5),
        half_day="first",
        counting_rule="working_days",
    ) == Decimal("0.5")
    assert chargeable_days(
        category="CL",
        start=date(2026, 1, 3),
        end=date(2026, 1, 3),
        half_day="first",
        counting_rule="working_days",
    ) == Decimal("0")
    assert chargeable_days(
        category="CL",
        start=date(2026, 1, 5),
        end=date(2026, 1, 5),
        half_day="second",
        counting_rule="working_days",
        closed_dates={date(2026, 1, 5)},
    ) == Decimal("0")


def test_half_day_cl_requires_a_configured_counting_rule():
    with pytest.raises(ValueError, match="counting rule is not configured"):
        chargeable_days(
            category="CL",
            start=date(2026, 1, 5),
            end=date(2026, 1, 5),
            half_day="first",
        )


def test_rh_requires_every_requested_day_in_published_calendar():
    assert chargeable_days(
        category="RH",
        start=date(2026, 1, 2),
        end=date(2026, 1, 3),
        restricted_dates={date(2026, 1, 2), date(2026, 1, 3)},
    ) == Decimal("2")
    with pytest.raises(ValueError, match="published RH calendar"):
        chargeable_days(
            category="RH",
            start=date(2026, 1, 2),
            end=date(2026, 1, 3),
            restricted_dates={date(2026, 1, 2)},
        )


def test_half_day_cl_requests_in_different_halves_do_not_overlap():
    common = {
        "first_start": date(2026, 2, 2),
        "first_end": date(2026, 2, 2),
        "second_start": date(2026, 2, 2),
        "second_end": date(2026, 2, 2),
        "first_category": "CL",
        "second_category": "CL",
    }
    assert not overlaps(**common, first_half="first", second_half="second")
    assert overlaps(**common, first_half="first", second_half="first")
    assert overlaps(**common, first_half="", second_half="second")


def test_cross_year_days_are_split_into_calendar_year_accounts():
    assert split_days_by_year(
        category="EL",
        start=date(2026, 12, 31),
        end=date(2027, 1, 2),
        counting_rule="continuous",
    ) == {2026: Decimal("1"), 2027: Decimal("2")}
