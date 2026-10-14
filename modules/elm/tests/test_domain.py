"""Pure Python Domain Unit Tests for ELM.

Validates core business rules (BR-EL-001..033), calculations,
state machine transitions, routing, overlap, and year-end policies.
Runs purely in memory without database dependencies.
"""
from datetime import date
from decimal import Decimal

import pytest

from modules.elm.domain import (
    categories as c,
    counting,
    overlap,
    policy,
    routing as r,
    state_machine as sm,
    year_end as ye,
)


# ============================================================================
# BR-EL-001, 002: Categories & Policy Parameters
# ============================================================================

def test_default_policy_parsing_and_eligibility():
    """BR-EL-001: Validate default policy parameters and employee eligibility."""
    p = policy.parse(policy.DEFAULT_PARAMS)
    assert p.annual_credit_for(c.FACULTY, c.CL) == Decimal("8")
    assert p.annual_credit_for(c.FACULTY, c.VL) == Decimal("60")
    assert p.annual_credit_for(c.STAFF, c.EL) == Decimal("30")

    # Faculty is eligible for VL; Staff is not
    p.check_eligible(c.FACULTY, c.VL)
    with pytest.raises(policy.NotEligible):
        p.check_eligible(c.STAFF, c.VL)


def test_invalid_policy_detection():
    """Policy validation flags invalid shapes, negative numbers, or invalid categories."""
    with pytest.raises(policy.PolicyInvalid):
        policy.parse("not a dict")

    with pytest.raises(policy.PolicyInvalid):
        policy.parse({"annual_credit": {c.FACULTY: {c.CL: -1}}, "eligible": {}})

    with pytest.raises(policy.PolicyInvalid):
        policy.parse({"annual_credit": {c.FACULTY: {"INVALID_CAT": 5}}, "eligible": {}})


# ============================================================================
# BR-EL-003, 006, 010, 011: Counting & Calendar Rules
# ============================================================================

def test_half_day_cl_calculation():
    """BR-EL-010: Half-day CL counts as exactly 0.5 days on working days."""
    cal = counting.Calendar()
    # 2026-10-15 is Thursday (working day)
    thursday = date(2026, 10, 15)
    days = counting.chargeable_days(c.CL, thursday, thursday, c.FIRST_HALF, cal)
    assert days == Decimal("0.5")

    # Half day cannot span multiple dates
    friday = date(2026, 10, 16)
    with pytest.raises(counting.InvalidPeriod):
        counting.chargeable_days(c.CL, thursday, friday, c.FIRST_HALF, cal)

    # Half day is only permitted for Casual Leave
    with pytest.raises(counting.InvalidPeriod):
        counting.chargeable_days(c.EL, thursday, thursday, c.FIRST_HALF, cal)


def test_continuous_counting_for_earned_leave():
    """BR-EL-011: EL/COL/VL include intervening weekends and closed holidays."""
    # From Friday 2026-10-16 to Monday 2026-10-19 = 4 continuous days
    start = date(2026, 10, 16)
    end = date(2026, 10, 19)
    cal = counting.Calendar(closed_holidays=frozenset({date(2026, 10, 19)}))
    days = counting.chargeable_days(c.EL, start, end, None, cal)
    assert days == Decimal("4")


def test_working_days_counting_for_casual_leave():
    """BR-EL-011: CL excludes intervening weekends and closed holidays."""
    # From Friday 2026-10-16 to Monday 2026-10-19:
    # Sat 17 and Sun 18 are weekends. If Mon 19 is closed holiday, only Fri 16 is charged.
    start = date(2026, 10, 16)
    end = date(2026, 10, 19)
    cal = counting.Calendar(closed_holidays=frozenset({date(2026, 10, 19)}))
    days = counting.chargeable_days(c.CL, start, end, None, cal)
    assert days == Decimal("1")  # Only Friday


def test_restricted_holiday_calendar_validation():
    """BR-EL-003: RH dates must be published in the restricted holidays calendar."""
    rh_date = date(2026, 11, 8)
    other_date = date(2026, 11, 9)
    cal = counting.Calendar(restricted_holidays=frozenset({rh_date}))

    counting.validate_rh_dates(rh_date, rh_date, cal)

    with pytest.raises(counting.InvalidPeriod):
        counting.validate_rh_dates(other_date, other_date, cal)


def test_vacation_leave_calendar_validation():
    """BR-EL-006: VL must be strictly inside a published vacation period."""
    cal = counting.Calendar(vacations=((date(2026, 12, 20), date(2027, 1, 5)),))

    # Within vacation period
    counting.validate_vacation(date(2026, 12, 22), date(2026, 12, 28), cal)

    # Outside vacation period
    with pytest.raises(counting.InvalidPeriod):
        counting.validate_vacation(date(2026, 11, 1), date(2026, 11, 5), cal)


# ============================================================================
# BR-EL-012, 014: Overlap Rules
# ============================================================================

def test_half_day_non_overlap():
    """BR-EL-012: First half and second half on the same date do not overlap."""
    d = date(2026, 10, 20)
    int1 = overlap.Interval(d, d, c.FIRST_HALF)
    int2 = overlap.Interval(d, d, c.SECOND_HALF)
    assert overlap.overlaps(int1, int2) is False

    # Same half on same date overlaps
    int3 = overlap.Interval(d, d, c.FIRST_HALF)
    assert overlap.overlaps(int1, int3) is True


def test_range_overlap():
    """Date ranges overlap according to standard interval boundaries."""
    a = overlap.Interval(date(2026, 10, 1), date(2026, 10, 10))
    b = overlap.Interval(date(2026, 10, 8), date(2026, 10, 15))
    c_int = overlap.Interval(date(2026, 10, 11), date(2026, 10, 20))
    assert overlap.overlaps(a, b) is True
    assert overlap.overlaps(a, c_int) is False


# ============================================================================
# BR-EL-016..020: Routing Resolution
# ============================================================================

def test_unit_head_final_routing():
    """BR-EL-016: CL and RH route only to Unit Head as final decision."""
    hierarchy = {
        "unit_heads": {"CSE": "HOD (CSE)"},
        "director_role": "Director",
        "establishment_role": "Deputy Registrar",
        "sanctioning": {"faculty": {"default": "Director"}, "staff": {"default": "Registrar"}},
    }
    steps = r.resolve_route(
        category=c.CL, kind=c.FACULTY, unit="CSE", applicant_roles=[], hierarchy=hierarchy,
    )
    assert len(steps) == 1
    assert steps[0].step == r.UNIT_HEAD
    assert steps[0].role == "HOD (CSE)"


def test_higher_sanction_routing():
    """BR-EL-017, 018: SCL/EL/COL/VL route through Unit Head, Establishment, and Sanction."""
    hierarchy = {
        "unit_heads": {"CSE": "HOD (CSE)"},
        "director_role": "Director",
        "establishment_role": "Deputy Registrar",
        "establishment_categories": [c.EL],
        "sanctioning": {"faculty": {"default": "Director"}, "staff": {"default": "Registrar"}},
    }
    steps = r.resolve_route(
        category=c.EL, kind=c.FACULTY, unit="CSE", applicant_roles=[], hierarchy=hierarchy,
    )
    assert [s.step for s in steps] == [r.UNIT_HEAD, r.ESTABLISHMENT, r.SANCTION]
    assert [s.role for s in steps] == ["HOD (CSE)", "Deputy Registrar", "Director"]


def test_director_self_sanction_routing():
    """BR-EL-020: Director applicant routes to single director self-sanction step."""
    hierarchy = {
        "unit_heads": {"CSE": "HOD (CSE)"},
        "director_role": "Director",
        "sanctioning": {"faculty": {"default": "Director"}},
    }
    steps = r.resolve_route(
        category=c.EL, kind=c.FACULTY, unit="CSE", applicant_roles=["Director"], hierarchy=hierarchy,
    )
    assert len(steps) == 1
    assert steps[0].step == r.DIRECTOR
    assert steps[0].role == "Director"


# ============================================================================
# State Machine & Lifecycle (WF-EL-01..05, BR-EL-021..028)
# ============================================================================

def test_state_machine_substitute_workflow():
    """Substitute must accept before request routes to Unit Head."""
    t = sm.resolve(sm.AWAITING_SUBSTITUTE, sm.SUBSTITUTE_ACCEPT, sm.SUBSTITUTE, sm.AWAITING_UNIT_HEAD)
    assert t.event == sm.SUBSTITUTE_ACCEPT

    # Unauthorized actor cannot accept substitution
    with pytest.raises(sm.ActorNotAllowed):
        sm.resolve(sm.AWAITING_SUBSTITUTE, sm.SUBSTITUTE_ACCEPT, sm.UNIT_HEAD, sm.AWAITING_UNIT_HEAD)


def test_state_machine_approval_and_rejection():
    """Unit Head can approve or reject CL/RH, or recommend SCL/EL."""
    t_app = sm.resolve(sm.AWAITING_UNIT_HEAD, sm.APPROVE, sm.UNIT_HEAD, sm.APPROVED)
    assert t_app.event == sm.APPROVE

    t_rec = sm.resolve(sm.AWAITING_UNIT_HEAD, sm.RECOMMEND, sm.UNIT_HEAD, sm.AWAITING_ESTABLISHMENT)
    assert t_rec.event == sm.RECOMMEND


def test_immediate_withdrawal_on_pending():
    """BR-EL-022: Employee can withdraw pending requests from any pending state."""
    for pending_state in (sm.AWAITING_SUBSTITUTE, sm.AWAITING_UNIT_HEAD, sm.AWAITING_SANCTION):
        t = sm.resolve(pending_state, sm.WITHDRAW, sm.EMPLOYEE, sm.WITHDRAWN)
        assert t.event == sm.WITHDRAW

    # Cannot withdraw approved leave
    with pytest.raises(sm.InvalidTransition):
        sm.resolve(sm.APPROVED, sm.WITHDRAW, sm.EMPLOYEE, sm.WITHDRAWN)


def test_cancellation_and_resumption_lifecycle():
    """BR-EL-023, 027: Cancellation and resumption lifecycle on approved leave."""
    # Cancellation request
    t_can = sm.resolve(sm.APPROVED, sm.REQUEST_CANCELLATION, sm.EMPLOYEE, sm.CANCELLATION_PENDING)
    assert t_can.event == sm.REQUEST_CANCELLATION

    # Cancellation approval
    t_can_app = sm.resolve(sm.CANCELLATION_PENDING, sm.CANCEL_APPROVE, sm.UNIT_HEAD, sm.CANCELLED)
    assert t_can_app.event == sm.CANCEL_APPROVE

    # Resumption submission & verification
    t_res = sm.resolve(sm.APPROVED, sm.SUBMIT_RESUMPTION, sm.EMPLOYEE, sm.RESUMPTION_PENDING)
    assert t_res.event == sm.SUBMIT_RESUMPTION

    t_res_ver = sm.resolve(sm.RESUMPTION_PENDING, sm.VERIFY_RESUMPTION, sm.VERIFIER, sm.CLOSED)
    assert t_res_ver.event == sm.VERIFY_RESUMPTION


# ============================================================================
# BR-EL-007, 008: Year-End Arithmetic
# ============================================================================

def test_vl_to_el_year_end_conversion():
    """BR-EL-007: Unused VL converts to EL at configured ratio (default 2:1)."""
    assert ye.vl_to_el(Decimal("60"), Decimal("2")) == Decimal("30.00")
    assert ye.vl_to_el(Decimal("15"), Decimal("2")) == Decimal("7.50")
    assert ye.vl_to_el(Decimal("0"), Decimal("2")) == Decimal("0")
