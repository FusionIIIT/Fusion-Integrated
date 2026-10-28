"""Pure-Python ELM rule tests — no database, so they run in milliseconds.

This is the payoff of the no-Django-in-domain rule (module-authoring-guide §3).
"""
from datetime import date
from decimal import Decimal

import pytest

from modules.leave.domain import categories as cat
from modules.leave.domain import state_machine as sm
from modules.leave.domain.categories import LeaveCategory
from modules.leave.domain.day_counting import (
    InvalidLeavePeriod,
    count_leave_days,
    half_day_overlaps,
)


def test_el_counts_weekends_continuously():
    # Fri 2026-01-02 .. Mon 2026-01-05 inclusive: weekend counts (rule §4).
    days = count_leave_days(category=LeaveCategory.EL,
                            starts_on=date(2026, 1, 2), ends_on=date(2026, 1, 5))
    assert days == Decimal("4")


def test_cl_counts_only_working_days():
    days = count_leave_days(category=LeaveCategory.CL,
                            starts_on=date(2026, 1, 2), ends_on=date(2026, 1, 5))
    assert days == Decimal("2")   # Mon and Fri only


def test_cl_excludes_closed_holidays():
    days = count_leave_days(category=LeaveCategory.CL,
                            starts_on=date(2026, 1, 5), ends_on=date(2026, 1, 6),
                            closed_holidays=frozenset({date(2026, 1, 6)}))
    assert days == Decimal("1")


def test_half_day_only_for_cl():
    with pytest.raises(InvalidLeavePeriod):
        count_leave_days(category=LeaveCategory.EL,
                         starts_on=date(2026, 1, 5), ends_on=date(2026, 1, 5),
                         half_day="first_half")
    assert count_leave_days(category=LeaveCategory.CL,
                            starts_on=date(2026, 1, 5), ends_on=date(2026, 1, 5),
                            half_day="first_half") == Decimal("0.5")


def test_first_and_second_half_do_not_overlap():
    assert half_day_overlaps("first_half", "second_half") is False
    assert half_day_overlaps("first_half", "first_half") is True


def test_vl_converts_to_el_at_two_to_one_including_fractions():
    assert cat.convert_vl_to_el(Decimal("7")) == Decimal("3.50")


def test_entitlements_match_baseline():
    assert cat.entitlement(LeaveCategory.CL) == Decimal("8")
    assert cat.entitlement(LeaveCategory.RH) == Decimal("2")
    assert cat.entitlement(LeaveCategory.SCL) == Decimal("15")
    assert cat.entitlement(LeaveCategory.EL) == Decimal("30")
    assert cat.entitlement(LeaveCategory.COL) == Decimal("20")
    assert cat.entitlement(LeaveCategory.VL) == Decimal("60")


def test_cl_and_rh_final_authority_is_unit_head():
    assert cat.final_authority(LeaveCategory.CL) is cat.FinalAuthority.UNIT_HEAD
    assert (cat.final_authority(LeaveCategory.EL)
            is cat.FinalAuthority.SANCTIONING_AUTHORITY)


def test_year_end_outcomes():
    assert cat.year_end_outcome(LeaveCategory.CL) is cat.YearEndOutcome.LAPSE
    assert (cat.year_end_outcome(LeaveCategory.EL)
            is cat.YearEndOutcome.CARRY_FORWARD)
    assert (cat.year_end_outcome(LeaveCategory.VL)
            is cat.YearEndOutcome.CONVERT_TO_EL)


def test_unit_head_recommends_but_cannot_sanction_higher_category():
    # A reviewer may move pending -> recommended, never straight to sanctioned
    # for a higher-sanction category through the unit-head edge.
    t = sm.validate_transition(sm.PENDING, sm.RECOMMENDED, actor=sm.UNIT_HEAD,
                               permissions=frozenset({"leave_management.leave.review"}))
    assert t.to == sm.RECOMMENDED


def test_illegal_transition_is_rejected():
    with pytest.raises(sm.InvalidTransition):
        sm.validate_transition(sm.SANCTIONED, sm.PENDING, actor=sm.APPLICANT,
                               permissions=frozenset({"*"}))


def test_wrong_actor_kind_is_rejected_even_with_permission():
    with pytest.raises(sm.ActorNotAllowed):
        sm.validate_transition(sm.PENDING, sm.SANCTIONED, actor=sm.APPLICANT,
                               permissions=frozenset({"leave_management.leave.sanction"}))


def test_only_pending_states_are_withdrawable():
    assert sm.may_withdraw(sm.PENDING) is True
    assert sm.may_withdraw(sm.SANCTIONED) is False
