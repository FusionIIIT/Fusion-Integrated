"""Pure rules, no database."""
from datetime import date
from decimal import Decimal

import pytest

from modules.leave.domain.accounting import Outcome, Reason, resumption_outcome, year_end_postings
from modules.leave.domain.categories import (
    Category,
    EmployeeKind,
    IneligibleCategory,
    annual_credit,
    check_eligible,
)
from modules.leave.domain.counting import Half, Interval, InvalidPeriod, leave_days, overlaps
from modules.leave.domain.workflow import (
    TRANSITIONS,
    Actor,
    Decision,
    Event,
    IllegalTransition,
    Route,
    State,
    WrongActor,
    entry_state,
    next_state,
    unit_head_event,
)

MON, FRI, NEXT_MON = date(2027, 1, 4), date(2027, 1, 8), date(2027, 1, 11)


def test_casual_leave_skips_weekends_and_closed_holidays():
    assert leave_days(Category.CL, FRI, NEXT_MON, Half.FULL, set()) == 2
    assert leave_days(Category.CL, MON, FRI, Half.FULL, {date(2027, 1, 6)}) == 4


def test_earned_leave_counts_every_day_in_between():
    assert leave_days(Category.EL, FRI, NEXT_MON, Half.FULL, {date(2027, 1, 9)}) == 4


def test_half_days_only_for_single_date_cl():
    assert leave_days(Category.CL, MON, MON, Half.FIRST, set()) == Decimal("0.5")
    with pytest.raises(InvalidPeriod):
        leave_days(Category.EL, MON, MON, Half.FIRST, set())
    with pytest.raises(InvalidPeriod):
        leave_days(Category.CL, MON, FRI, Half.SECOND, set())


def test_period_on_weekend_only_and_backwards_period_are_refused():
    with pytest.raises(InvalidPeriod):
        leave_days(Category.CL, date(2027, 1, 9), date(2027, 1, 10), Half.FULL, set())
    with pytest.raises(InvalidPeriod):
        leave_days(Category.EL, FRI, MON, Half.FULL, set())


def test_different_cl_halves_on_one_date_do_not_overlap():
    assert not overlaps(Interval(MON, MON, Half.FIRST), Interval(MON, MON, Half.SECOND))
    assert overlaps(Interval(MON, MON, Half.FIRST), Interval(MON, MON, Half.FIRST))
    assert overlaps(Interval(MON, MON, Half.FIRST), Interval(MON, FRI))
    assert not overlaps(Interval(MON, FRI), Interval(NEXT_MON, NEXT_MON))


def test_vl_is_faculty_only_and_faculty_get_no_direct_el():
    with pytest.raises(IneligibleCategory):
        check_eligible(Category.VL, EmployeeKind.STAFF)
    assert annual_credit(Category.EL, EmployeeKind.FACULTY, Decimal(30)) == 0
    assert annual_credit(Category.EL, EmployeeKind.STAFF, Decimal(30)) == 30
    assert annual_credit(Category.VL, EmployeeKind.STAFF, Decimal(60)) == 0


@pytest.mark.parametrize("state", list(State))
@pytest.mark.parametrize("event", list(Event))
def test_every_pair_outside_the_table_is_refused(state, event):
    if (state, event) in TRANSITIONS:
        actor, target = TRANSITIONS[(state, event)]
        assert next_state(state, event, actor) is target
        wrong = next(a for a in Actor if a is not actor)
        with pytest.raises(WrongActor):
            next_state(state, event, wrong)
    else:
        with pytest.raises(IllegalTransition):
            next_state(state, event, Actor.APPLICANT)


def test_terminal_states_have_no_way_out():
    for terminal in (State.REJECTED, State.WITHDRAWN, State.CANCELLED):
        assert not [k for k in TRANSITIONS if k[0] is terminal]


def test_approved_leave_cannot_be_withdrawn():
    with pytest.raises(IllegalTransition):
        next_state(State.APPROVED, Event.WITHDRAW, Actor.APPLICANT)


def test_entry_state_follows_route():
    plain = Route(unit_head_final=True, establishment=False, director_self=False)
    director = Route(unit_head_final=False, establishment=False, director_self=True)
    assert entry_state(plain, has_substitute=True) is State.AWAITING_SUBSTITUTE
    assert entry_state(plain, has_substitute=False) is State.AWAITING_UNIT_HEAD
    assert entry_state(director, has_substitute=False) is State.AWAITING_FINAL


def test_unit_head_decides_cl_but_only_recommends_el():
    final = Route(unit_head_final=True, establishment=False, director_self=False)
    higher = Route(unit_head_final=False, establishment=True, director_self=False)
    assert unit_head_event(final, Decision.REJECT) is Event.UNIT_HEAD_REJECT
    assert unit_head_event(higher, Decision.NOT_RECOMMENDED) is \
        Event.RECOMMEND_TO_ESTABLISHMENT
    with pytest.raises(IllegalTransition):
        unit_head_event(final, Decision.RECOMMENDED)
    with pytest.raises(IllegalTransition):
        unit_head_event(higher, Decision.APPROVE)


def test_year_end_lapses_converts_and_carries():
    postings = year_end_postings(2026, {
        Category.CL: Decimal(3), Category.VL: Decimal(15), Category.EL: Decimal(40),
        Category.COL: Decimal(0)})
    got = {(p.category, p.year, p.reason): p.days for p in postings}
    assert got[(Category.CL, 2026, Reason.LAPSE)] == -3
    assert got[(Category.VL, 2026, Reason.CONVERT_OUT)] == -15
    assert got[(Category.EL, 2027, Reason.CONVERT_IN)] == Decimal("7.5")
    assert got[(Category.EL, 2027, Reason.CARRY_IN)] == 40
    assert not [p for p in postings if p.category is Category.COL]


def test_resumption_outcomes():
    end = date(2027, 6, 10)
    assert resumption_outcome(Category.EL, end, end) == (Outcome.NORMAL, 0)
    assert resumption_outcome(Category.EL, end, date(2027, 6, 7)) == (Outcome.EARLY, 3)
    assert resumption_outcome(Category.VL, end, date(2027, 6, 12)) == (Outcome.LATE, -2)
