from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from modules.leave.domain import categories, state_machine
from modules.leave.domain.categories import CATEGORIES, FACULTY_ONLY, NON_FACULTY_ONLY
from modules.leave.domain.counting import count_days, overlaps
from modules.leave.domain.state_machine import (
    InvalidTransition,
    Transition,
)


def test_is_eligible_for_every_category_faculty():
    """BR-EL-001 is_eligible for every category for faculty"""
    for category in CATEGORIES:
        assert categories.is_eligible(category, True)


def test_is_eligible_for_every_category_non_faculty():
    """BR-EL-001 is_eligible for every category for non-faculty"""
    for category in CATEGORIES:
        if category in FACULTY_ONLY:
            assert not categories.is_eligible(category, False)
        elif category in NON_FACULTY_ONLY:
            assert categories.is_eligible(category, False)


def test_half_day_cl_counts_0_5():
    """BR-EL-010 a CL half day counts 0.5"""
    start = date(2023, 10, 6)  # Friday
    end = date(2023, 10, 7)  # Monday
    holidays = set()
    assert count_days("CL", start, end, True, holidays) == Decimal("0.5")


def test_continuous_counting_el_col_vl():
    """BR-EL-011 EL/COL/VL count weekends and holidays continuously while CL/RH/SCL skip Saturdays, Sundays and holidays"""
    start = date(2023, 10, 6)  # Friday
    end = date(2023, 10, 9)  # Monday
    holidays = {date(2023, 10, 7)}  # Saturday
    assert count_days("EL", start, end, False, holidays) == Decimal("4")
    assert count_days("COL", start, end, False, holidays) == Decimal("4")
    assert count_days("VL", start, end, False, holidays) == Decimal("4")


def test_continuous_counting_cl_rh_scl():
    """BR-EL-011 CL/RH/SCL skip Saturdays, Sundays and holidays"""
    start = date(2023, 10, 6)  # Friday
    end = date(2023, 10, 9)  # Monday
    holidays = {date(2023, 10, 7)}  # Saturday
    assert count_days("CL", start, end, False, holidays) == Decimal("2")
    assert count_days("RH", start, end, False, holidays) == Decimal("2")
    assert count_days("SCL", start, end, False, holidays) == Decimal("2")


def test_overlaps_for_overlapping_ranges():
    """BR-EL-012 overlaps() for overlapping ranges"""
    assert overlaps(1, 5, 3, 7)


def test_overlaps_for_touching_ranges():
    """BR-EL-012 overlaps() for touching ranges"""
    assert overlaps(1, 5, 5, 7)


def test_overlaps_for_disjoint_ranges():
    """BR-EL-012 overlaps() for disjoint ranges"""
    assert not overlaps(1, 3, 4, 6)


def test_state_machine_unit_review_to_approved():
    """state machine allows unit_review->approved"""
    assert state_machine.can_transition("unit_review", "approved") is True


def test_state_machine_routing_to_sanction():
    """state machine allows routing->sanction"""
    assert state_machine.resolve("routing", "sanction") == Transition(
        "routing", "sanction", "leave.request.sanction", frozenset({"registrar", "director"})
    )


def test_state_machine_approved_to_cancelled():
    """state machine allows approved->cancelled"""
    assert state_machine.resolve("approved", "cancelled") == Transition(
        "approved", "cancelled", "leave.request.cancel", frozenset({"student"})
    )


def test_state_machine_refuses_approved_to_unit_review():
    """state machine refuses approved->unit_review"""
    with pytest.raises(InvalidTransition):
        state_machine.resolve("approved", "unit_review")


def test_state_machine_refuses_withdrawn_to_approved():
    """state machine refuses withdrawn->approved"""
    with pytest.raises(InvalidTransition):
        state_machine.resolve("withdrawn", "approved")


def test_assert_transition_raises_invalid_transition():
    """assert_transition raises InvalidTransition"""
    with pytest.raises(InvalidTransition):
        state_machine.assert_transition("approved", "unit_review")
