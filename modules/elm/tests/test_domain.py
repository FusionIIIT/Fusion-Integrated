"""Pure-domain tests: no database, no Django."""
from datetime import date
from decimal import Decimal

from modules.elm.domain.categories import (
    LeaveCategory,
    convert_vl_to_el,
    count_days,
    entitlement,
    overlaps,
)
from modules.elm.domain.state_machine import TERMINAL, TRANSITIONS, LeaveStatus, transition_for


def test_cl_entitlement_is_eight():
    assert entitlement(LeaveCategory.CL, kind="faculty") == Decimal("8")


def test_el_is_non_faculty_only():
    assert entitlement(LeaveCategory.EL, kind="faculty") == Decimal("0")
    assert entitlement(LeaveCategory.EL, kind="staff") == Decimal("30")


def test_vl_is_faculty_only():
    assert entitlement(LeaveCategory.VL, kind="faculty") == Decimal("60")
    assert entitlement(LeaveCategory.VL, kind="staff") == Decimal("0")


def test_continuous_counting_el_includes_weekend():
    # 2026-10-09 is a Friday; a Fri-Mon EL spans a weekend.
    start, end = date(2026, 10, 9), date(2026, 10, 12)
    assert count_days(LeaveCategory.EL, start, end) == Decimal("4")


def test_cl_skips_weekend():
    start, end = date(2026, 10, 9), date(2026, 10, 12)
    assert count_days(LeaveCategory.CL, start, end) == Decimal("2")


def test_half_day_cl_is_half():
    d = date(2026, 10, 9)
    assert count_days(LeaveCategory.CL, d, d, half="first") == Decimal("0.5")


def test_overlap_same_day_different_halves_not_overlapping():
    d = date(2026, 10, 9)
    assert not overlaps(d, d, "first", d, d, "second")


def test_overlap_same_day_same_half_overlapping():
    d = date(2026, 10, 9)
    assert overlaps(d, d, "first", d, d, "first")


def test_vl_to_el_fraction_is_preserved():
    assert convert_vl_to_el(Decimal("5")) == Decimal("2.5")


def test_terminal_states_have_no_outgoing_transitions():
    for status in TERMINAL:
        assert status.is_final
        assert not [t for t in TRANSITIONS if t.frm == status]


def test_submitted_can_be_approved_and_withdrawn():
    assert transition_for(LeaveStatus.SUBMITTED, LeaveStatus.APPROVED)
    assert transition_for(LeaveStatus.SUBMITTED, LeaveStatus.WITHDRAWN)
