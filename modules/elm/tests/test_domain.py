"""Pure-domain tests: no database, no Django."""
from datetime import date
from decimal import Decimal

import pytest

from modules.elm.domain.categories import (
    LeaveCategory,
    carries_forward,
    convert_vl_to_el,
    count_days,
    entitlement,
    is_continuous,
    overlaps,
    requires_higher_sanction,
    supports_half_day,
)
from modules.elm.domain.state_machine import (
    TERMINAL,
    TRANSITIONS,
    InvalidTransition,
    LeaveStatus,
    transition_for,
)


def test_cl_entitlement_is_eight():
    assert entitlement(LeaveCategory.CL, kind="faculty") == Decimal("8")
    assert entitlement(LeaveCategory.CL, kind="staff") == Decimal("8")


def test_rh_entitlement_is_two():
    assert entitlement(LeaveCategory.RH, kind="faculty") == Decimal("2")
    assert entitlement(LeaveCategory.RH, kind="staff") == Decimal("2")


def test_scl_entitlement_is_fifteen():
    assert entitlement(LeaveCategory.SCL, kind="faculty") == Decimal("15")
    assert entitlement(LeaveCategory.SCL, kind="staff") == Decimal("15")


def test_col_entitlement_is_twenty():
    assert entitlement(LeaveCategory.COL, kind="faculty") == Decimal("20")
    assert entitlement(LeaveCategory.COL, kind="staff") == Decimal("20")


def test_el_is_non_faculty_only():
    assert entitlement(LeaveCategory.EL, kind="faculty") == Decimal("0")
    assert entitlement(LeaveCategory.EL, kind="staff") == Decimal("30")


def test_vl_is_faculty_only():
    assert entitlement(LeaveCategory.VL, kind="faculty") == Decimal("60")
    assert entitlement(LeaveCategory.VL, kind="staff") == Decimal("0")


def test_carries_forward_rules():
    assert carries_forward(LeaveCategory.EL) is True
    assert carries_forward(LeaveCategory.COL) is True
    assert carries_forward(LeaveCategory.CL) is False
    assert carries_forward(LeaveCategory.RH) is False
    assert carries_forward(LeaveCategory.SCL) is False
    assert carries_forward(LeaveCategory.VL) is False


def test_is_continuous_rules():
    assert is_continuous(LeaveCategory.EL) is True
    assert is_continuous(LeaveCategory.COL) is True
    assert is_continuous(LeaveCategory.VL) is True
    assert is_continuous(LeaveCategory.CL) is False
    assert is_continuous(LeaveCategory.RH) is False
    assert is_continuous(LeaveCategory.SCL) is False


def test_requires_higher_sanction():
    assert requires_higher_sanction(LeaveCategory.CL) is False
    assert requires_higher_sanction(LeaveCategory.RH) is False
    assert requires_higher_sanction(LeaveCategory.SCL) is True
    assert requires_higher_sanction(LeaveCategory.EL) is True
    assert requires_higher_sanction(LeaveCategory.COL) is True
    assert requires_higher_sanction(LeaveCategory.VL) is True


def test_supports_half_day():
    assert supports_half_day(LeaveCategory.CL) is True
    assert supports_half_day(LeaveCategory.EL) is False
    assert supports_half_day(LeaveCategory.VL) is False


def test_continuous_counting_el_includes_weekend():
    # 2026-10-09 is a Friday; a Fri-Mon EL spans a weekend.
    start, end = date(2026, 10, 9), date(2026, 10, 12)
    assert count_days(LeaveCategory.EL, start, end) == Decimal("4")


def test_cl_skips_weekend():
    start, end = date(2026, 10, 9), date(2026, 10, 12)
    assert count_days(LeaveCategory.CL, start, end) == Decimal("2")


def test_cl_skips_holidays():
    start, end = date(2026, 10, 5), date(2026, 10, 9)  # Mon-Fri
    hols = frozenset([date(2026, 10, 6)])              # Tuesday holiday
    assert count_days(LeaveCategory.CL, start, end, holidays=hols) == Decimal("4")


def test_half_day_cl_is_half():
    d = date(2026, 10, 9)
    assert count_days(LeaveCategory.CL, d, d, half="first") == Decimal("0.5")
    assert count_days(LeaveCategory.CL, d, d, half="second") == Decimal("0.5")


def test_half_day_multi_date_raises_error():
    with pytest.raises(ValueError, match="Half-day leave must be for a single date"):
        count_days(LeaveCategory.CL, date(2026, 10, 9), date(2026, 10, 10), half="first")


def test_half_day_unsupported_category_raises_error():
    d = date(2026, 10, 9)
    with pytest.raises(ValueError, match="does not support half-day"):
        count_days(LeaveCategory.EL, d, d, half="first")


def test_end_before_start_raises_error():
    with pytest.raises(ValueError, match="end date precedes start date"):
        count_days(LeaveCategory.CL, date(2026, 10, 10), date(2026, 10, 9))


def test_overlap_same_day_different_halves_not_overlapping():
    d = date(2026, 10, 9)
    assert not overlaps(d, d, "first", d, d, "second")


def test_overlap_same_day_same_half_overlapping():
    d = date(2026, 10, 9)
    assert overlaps(d, d, "first", d, d, "first")


def test_overlap_range_cases():
    assert overlaps(date(2026, 10, 1), date(2026, 10, 5), "full",
                    date(2026, 10, 4), date(2026, 10, 8), "full")
    assert not overlaps(date(2026, 10, 1), date(2026, 10, 5), "full",
                        date(2026, 10, 6), date(2026, 10, 8), "full")


def test_vl_to_el_fraction_is_preserved():
    assert convert_vl_to_el(Decimal("5")) == Decimal("2.5")
    assert convert_vl_to_el(Decimal("60")) == Decimal("30")


def test_terminal_states_have_no_outgoing_transitions():
    for status in TERMINAL:
        assert status.is_final
        assert not [t for t in TRANSITIONS if t.frm == status]


def test_valid_transitions():
    # Application creation
    assert transition_for(None, LeaveStatus.SUBMITTED)
    # Direct decision
    assert transition_for(LeaveStatus.SUBMITTED, LeaveStatus.APPROVED)
    assert transition_for(LeaveStatus.SUBMITTED, LeaveStatus.REJECTED)
    # Unit Head recommendation
    assert transition_for(LeaveStatus.SUBMITTED, LeaveStatus.FORWARDED)
    assert transition_for(LeaveStatus.FORWARDED, LeaveStatus.APPROVED)
    assert transition_for(LeaveStatus.FORWARDED, LeaveStatus.REJECTED)
    # Withdrawal
    assert transition_for(LeaveStatus.SUBMITTED, LeaveStatus.WITHDRAWN)
    assert transition_for(LeaveStatus.FORWARDED, LeaveStatus.WITHDRAWN)
    # Cancellation
    assert transition_for(LeaveStatus.APPROVED, LeaveStatus.CANCELLATION_REQUESTED)
    assert transition_for(LeaveStatus.CANCELLATION_REQUESTED, LeaveStatus.CANCELLED)
    assert transition_for(LeaveStatus.CANCELLATION_REQUESTED, LeaveStatus.APPROVED)
    # Resumption
    assert transition_for(LeaveStatus.APPROVED, LeaveStatus.RESUMPTION_REQUESTED)
    assert transition_for(LeaveStatus.RESUMPTION_REQUESTED, LeaveStatus.RESUMED)


def test_invalid_transitions():
    with pytest.raises(InvalidTransition):
        transition_for(LeaveStatus.REJECTED, LeaveStatus.APPROVED)
    with pytest.raises(InvalidTransition):
        transition_for(LeaveStatus.CANCELLED, LeaveStatus.APPROVED)
    with pytest.raises(InvalidTransition):
        transition_for(LeaveStatus.APPROVED, LeaveStatus.SUBMITTED)
