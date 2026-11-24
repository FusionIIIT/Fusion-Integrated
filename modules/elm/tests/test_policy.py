"""Unit tests for ELM domain rules."""

from datetime import date
from decimal import Decimal

import pytest

from modules.elm.domain.policy import (
    convert_vl_to_el,
    count_days,
    eligible,
    overlaps,
    remaining,
    requires_higher_sanction,
)


def test_entitlement_eligibility():
    assert eligible("VL", "faculty")
    assert not eligible("VL", "staff")
    assert eligible("CL", "staff")
    assert eligible("EL", "faculty")
    assert not eligible("UNSUPPORTED", "faculty")


def test_sanction_hierarchy_requirement():
    assert not requires_higher_sanction("CL")
    assert not requires_higher_sanction("RH")
    assert requires_higher_sanction("SCL")
    assert requires_higher_sanction("EL")
    assert requires_higher_sanction("COL")
    assert requires_higher_sanction("VL")


def test_half_day_cl_and_weekends():
    assert count_days("CL", date(2026, 10, 12), date(2026, 10, 12), "FIRST") == Decimal("0.5")
    assert count_days("CL", date(2026, 10, 10), date(2026, 10, 12)) == Decimal("1")
    with pytest.raises(ValueError):
        count_days("EL", date(2026, 10, 12), date(2026, 10, 12), "FIRST")


def test_continuous_leave_counts_weekends_and_closed_days():
    closed = frozenset({date(2026, 10, 12)})
    assert count_days("EL", date(2026, 10, 9), date(2026, 10, 12), closed_days=closed) == Decimal(
        "4"
    )
    assert count_days("CL", date(2026, 10, 9), date(2026, 10, 12), closed_days=closed) == Decimal(
        "1"
    )


def test_half_day_overlap_exception():
    day = date(2026, 10, 12)
    assert not overlaps(day, day, day, day, "FIRST", "SECOND")
    assert overlaps(day, day, day, day, "FIRST", "NONE")
    assert overlaps(day, day, day, day, "FIRST", "FIRST")


def test_other_day_ranges_overlap_only_if_intersecting():
    assert not overlaps(date(2026, 1, 1), date(2026, 1, 3), date(2026, 1, 5), date(2026, 1, 7))
    assert overlaps(date(2026, 1, 1), date(2026, 1, 5), date(2026, 1, 4), date(2026, 1, 6))


def test_remaining_balance():
    assert remaining(Decimal("8"), Decimal("1"), Decimal("0.5")) == Decimal("6.5")
    with pytest.raises(ValueError):
        remaining(Decimal("2"), Decimal("1"), Decimal("2"))


def test_vl_to_el_conversion_and_cap():
    credited, updated = convert_vl_to_el(Decimal("30"), Decimal("280"), Decimal("300"))
    assert credited == Decimal("15")
    assert updated == Decimal("295")
    capped_credit, capped_total = convert_vl_to_el(Decimal("30"), Decimal("290"), Decimal("300"))
    assert capped_credit == Decimal("10")
    assert capped_total == Decimal("300")
