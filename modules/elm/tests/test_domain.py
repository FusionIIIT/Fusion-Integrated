"""Rules with no database."""
from datetime import date
from decimal import Decimal

import pytest

from modules.elm.domain import policy
from modules.elm.domain import state_machine as sm

FRI, SAT, MON = date(2026, 1, 9), date(2026, 1, 10), date(2026, 1, 12)


def test_category_applicability_by_kind():
    policy.check_category(policy.VL, policy.FACULTY)
    policy.check_category(policy.EL, policy.STAFF)
    with pytest.raises(policy.PolicyViolation) as exc:
        policy.check_category(policy.VL, policy.STAFF)
    assert exc.value.code == "category_not_applicable"
    with pytest.raises(policy.PolicyViolation):
        policy.check_category(policy.CL, "student")
    with pytest.raises(policy.PolicyViolation):
        policy.check_category("ML", policy.FACULTY)


def test_only_staff_get_el_credit_and_only_faculty_vl():
    assert policy.EL in policy.credited_categories(policy.STAFF)
    assert policy.EL not in policy.credited_categories(policy.FACULTY)
    assert policy.VL in policy.credited_categories(policy.FACULTY)
    assert policy.credited_categories("student") == ()


@pytest.mark.parametrize("category,expected", [
    (policy.CL, Decimal(2)), (policy.SCL, Decimal(2)),
    (policy.EL, Decimal(4)), (policy.COL, Decimal(4)), (policy.VL, Decimal(4)),
])
def test_weekends_count_only_for_continuous_categories(category, expected):
    assert policy.count_days(category, FRI, MON, None, set()) == expected


def test_closed_holiday_skipped_for_cl_counted_for_el():
    assert policy.count_days(policy.CL, FRI, MON, None, {MON}) == 1
    assert policy.count_days(policy.EL, FRI, MON, None, {MON}) == 4


def test_half_day_cl_is_half():
    assert policy.count_days(policy.CL, FRI, FRI, "first", set()) == Decimal("0.5")
    with pytest.raises(policy.PolicyViolation):
        policy.check_period(policy.EL, FRI, FRI, "first")
    with pytest.raises(policy.PolicyViolation):
        policy.check_period(policy.CL, FRI, MON, "first")


def test_weekend_only_cl_is_refused():
    with pytest.raises(policy.PolicyViolation):
        policy.check_counted(policy.count_days(policy.CL, SAT, SAT, None, set()))


def test_overlap_and_half_day_exception():
    a = policy.Interval(FRI, FRI, "first")
    assert not policy.overlaps(a, policy.Interval(FRI, FRI, "second"))
    assert policy.overlaps(a, policy.Interval(FRI, FRI, "first"))
    assert policy.overlaps(a, policy.Interval(FRI, MON))
    assert not policy.overlaps(policy.Interval(FRI, FRI), policy.Interval(MON, MON))


def test_rh_must_be_published_restricted_holiday():
    policy.check_restricted_holidays(FRI, FRI, {FRI})
    with pytest.raises(policy.PolicyViolation):
        policy.check_restricted_holidays(FRI, MON, {FRI})


def test_vl_inside_vacation_only():
    policy.check_vacation(FRI, MON, [(date(2026, 1, 1), date(2026, 1, 31))])
    with pytest.raises(policy.PolicyViolation):
        policy.check_vacation(FRI, MON, [(date(2026, 1, 10), date(2026, 1, 31))])


def test_balance_and_conversion():
    policy.check_balance(Decimal(2), Decimal(2))
    with pytest.raises(policy.PolicyViolation):
        policy.check_balance(Decimal("2.5"), Decimal(2))
    assert policy.vl_to_el(Decimal(15)) == Decimal("7.5")
    assert policy.resumption_adjustment(FRI, MON) == 3
    assert policy.resumption_adjustment(MON, FRI) == -3
    assert policy.resumption_adjustment(FRI, FRI) == 0


ALL_STATES = sorted({t.frm for t in sm.TRANSITIONS} | {t.to for t in sm.TRANSITIONS})
ACTORS = sorted({t.actor for t in sm.TRANSITIONS})


@pytest.mark.parametrize("frm", ALL_STATES)
@pytest.mark.parametrize("to", ALL_STATES)
def test_every_pair_not_in_table_is_refused(frm, to):
    if sm.is_legal(frm, to):
        return
    with pytest.raises(sm.InvalidTransition):
        sm.resolve(frm, to, sm.EMPLOYEE)


@pytest.mark.parametrize("t", sm.TRANSITIONS, ids=lambda t: f"{t.frm}->{t.to}")
def test_every_edge_refuses_every_other_actor(t):
    assert sm.resolve(t.frm, t.to, t.actor) is t
    for actor in ACTORS:
        if actor != t.actor:
            with pytest.raises(sm.ActorNotAllowed):
                sm.resolve(t.frm, t.to, actor)


def test_terminal_states_have_no_exit_except_cancellation():
    exits = {t.frm for t in sm.TRANSITIONS}
    assert exits & sm.TERMINAL == {sm.APPROVED}
    assert [t.to for t in sm.TRANSITIONS if t.frm == sm.APPROVED] == [sm.CANCELLED]


def test_withdrawal_reaches_from_every_pending_state():
    for s in sm.PENDING:
        assert sm.is_legal(s, sm.WITHDRAWN)
    assert not sm.is_legal(sm.APPROVED, sm.WITHDRAWN)
