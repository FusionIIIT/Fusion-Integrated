"""Unit tests for ELM domain rules."""

from datetime import date
from decimal import Decimal

import pytest

from modules.elm.domain.policy import (
    convert_vl_to_el,
    count_days,
    eligible,
    is_director,
    overlaps,
    remaining,
    requires_higher_sanction,
    validate_substitute_nomination,
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


def test_vl_to_el_fractional_conversion_br_el_007():
    # Zero unavailed VL
    zero_credit, zero_updated = convert_vl_to_el(Decimal("0"), Decimal("100"), Decimal("300"))
    assert zero_credit == Decimal("0")
    assert zero_updated == Decimal("100")

    # Odd values: 15 VL -> 7.5 EL, 1 VL -> 0.5 EL, 7 VL -> 3.5 EL
    credited, updated = convert_vl_to_el(Decimal("15"), Decimal("0"), Decimal("300"))
    assert credited == Decimal("7.5")
    assert updated == Decimal("7.5")

    credited_half, updated_half = convert_vl_to_el(Decimal("1"), Decimal("10"), Decimal("300"))
    assert credited_half == Decimal("0.5")
    assert updated_half == Decimal("10.5")

    c7, u7 = convert_vl_to_el(Decimal("7"), Decimal("20"), Decimal("300"))
    assert c7 == Decimal("3.5")
    assert u7 == Decimal("23.5")

    # Fractional unavailed input: 15.5 VL -> 7.75 EL
    c_frac, u_frac = convert_vl_to_el(Decimal("15.5"), Decimal("0"), Decimal("300"))
    assert c_frac == Decimal("7.75")
    assert u_frac == Decimal("7.75")

    # Cap boundaries: exactly hitting cap, partial room, zero room, above cap
    c_exact, u_exact = convert_vl_to_el(Decimal("20"), Decimal("290"), Decimal("300"))
    assert c_exact == Decimal("10.0")
    assert u_exact == Decimal("300.0")

    capped_frac, capped_total = convert_vl_to_el(Decimal("15"), Decimal("295"), Decimal("300"))
    assert capped_frac == Decimal("5.0")
    assert capped_total == Decimal("300.0")

    c_full, u_full = convert_vl_to_el(Decimal("20"), Decimal("300"), Decimal("300"))
    assert c_full == Decimal("0.0")
    assert u_full == Decimal("300.0")

    # Invalid values raise ValueError
    with pytest.raises(ValueError, match=r"Balances and caps must be non-negative\."):
        convert_vl_to_el(Decimal("-1"), Decimal("10"), Decimal("300"))
    with pytest.raises(ValueError, match=r"Balances and caps must be non-negative\."):
        convert_vl_to_el(Decimal("10"), Decimal("-5"), Decimal("300"))
    with pytest.raises(ValueError, match=r"Balances and caps must be non-negative\."):
        convert_vl_to_el(Decimal("10"), Decimal("10"), Decimal("0"))


def test_substitute_overlap_date_ranges_br_el_014():
    # Boundary overlap: existing ends Oct 14, new starts Oct 14 -> overlaps
    assert overlaps(date(2026, 10, 12), date(2026, 10, 14), date(2026, 10, 14), date(2026, 10, 16))
    # Boundary overlap: existing starts Oct 14, new ends Oct 14 -> overlaps
    assert overlaps(date(2026, 10, 14), date(2026, 10, 16), date(2026, 10, 12), date(2026, 10, 14))
    # Strictly non-overlapping adjacent ranges -> does NOT overlap
    assert not overlaps(date(2026, 10, 12), date(2026, 10, 14), date(2026, 10, 15), date(2026, 10, 16))
    # Enclosed range -> overlaps
    assert overlaps(date(2026, 10, 10), date(2026, 10, 20), date(2026, 10, 12), date(2026, 10, 14))
    # Enclosing range -> overlaps
    assert overlaps(date(2026, 10, 12), date(2026, 10, 14), date(2026, 10, 10), date(2026, 10, 20))
    # Same day half-day exception: FIRST and SECOND do not overlap
    assert not overlaps(
        date(2026, 10, 14), date(2026, 10, 14), date(2026, 10, 14), date(2026, 10, 14), "FIRST", "SECOND"
    )
    # Same day same half-day: FIRST and FIRST overlap
    assert overlaps(
        date(2026, 10, 14), date(2026, 10, 14), date(2026, 10, 14), date(2026, 10, 14), "FIRST", "FIRST"
    )


def test_director_identification_br_el_020():
    assert is_director("Director")
    assert is_director("director ")
    assert is_director("DIRECTOR")
    assert not is_director("Deputy Director")
    assert not is_director("Assistant Professor")
    assert not is_director("")
    assert not is_director(None)


def test_substitute_nomination_validation_br_el_014():
    validate_substitute_nomination(101, 102)
    with pytest.raises(ValueError, match=r"Applicant cannot be their own substitute\."):
        validate_substitute_nomination(101, 101)

