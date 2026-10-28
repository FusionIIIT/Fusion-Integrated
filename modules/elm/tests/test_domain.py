from datetime import date
from decimal import Decimal

import pytest

from modules.elm.domain.rules import (
    annual_entitlement,
    count_leave_days,
    overlaps,
    year_end_credit,
)


def test_half_day_is_only_valid_for_one_day_cl():
    assert count_leave_days(date(2026, 10, 29), date(2026, 10, 29),
                            "CL", half_day=True) == Decimal("0.5")
    with pytest.raises(ValueError, match="single-day CL"):
        count_leave_days(date(2026, 10, 29), date(2026, 10, 30),
                         "CL", half_day=True)
    with pytest.raises(ValueError, match="single-day CL"):
        count_leave_days(date(2026, 10, 29), date(2026, 10, 29),
                         "EL", half_day=True)


def test_cl_counts_weekdays_and_excludes_closed_holidays():
    assert count_leave_days(
        date(2026, 10, 29), date(2026, 11, 3), "CL",
        holidays={date(2026, 10, 30)},
    ) == Decimal("3")


def test_continuous_leave_counts_weekends_and_holidays():
    assert count_leave_days(
        date(2026, 10, 30), date(2026, 11, 2), "EL",
        holidays={date(2026, 10, 30)},
    ) == Decimal("4")


def test_only_opposite_halves_of_same_day_cl_do_not_overlap():
    common = {
        "start": date(2026, 10, 29),
        "end": date(2026, 10, 29),
        "other_start": date(2026, 10, 29),
        "other_end": date(2026, 10, 29),
        "category": "CL",
    }
    assert not overlaps(
        **common, half_day_part="first_half", other_half_day_part="second_half")
    assert overlaps(
        **common, half_day_part="first_half", other_half_day_part="first_half")


def test_year_end_converts_vl_at_two_to_one_and_carries_only_eligible_types():
    assert year_end_credit("VL", Decimal("3.5")) == (
        Decimal("0"), Decimal("1.75"))
    assert year_end_credit("CL", Decimal("3")) == (
        Decimal("0"), Decimal("0"))
    assert year_end_credit("EL", Decimal("3")) == (
        Decimal("3"), Decimal("0"))
    assert year_end_credit("COL", Decimal("-1")) == (
        Decimal("0"), Decimal("0"))


def test_annual_entitlement_respects_faculty_leave_categories():
    assert annual_entitlement("EL", "faculty") == Decimal("0")
    assert annual_entitlement("VL", "faculty") == Decimal("60")
    assert annual_entitlement("EL", "staff") == Decimal("30")
    assert annual_entitlement("VL", "staff") == Decimal("0")
