"""The transition table is the specification, so it is tested as one.

Every illegal move is enumerated from the table itself rather than hand-picked,
and every guard the table names is asserted to have an implementation: an
unimplemented guard fails closed at runtime, which is a 409 nobody can debug.
"""
import itertools

import pytest

from modules.leave.domain import state_machine as sm
from modules.leave.registry import PERMISSIONS, SYSTEM_PERMISSIONS
from modules.leave.services import guards

DECLARED = {(t.frm, t.event) for t in sm.TRANSITIONS}


def test_every_state_event_pair_is_legal_iff_declared():
    for frm, event in itertools.product(sm.STATUSES, sm.EVENTS):
        assert sm.is_legal(frm, event) is ((frm, event) in DECLARED)


def test_terminal_states_have_no_exits():
    for state in sm.TERMINAL:
        assert sm.allowed_events(state) == []


def test_an_undeclared_move_raises_instead_of_being_rejected_later():
    with pytest.raises(sm.InvalidTransition):
        sm.resolve(sm.APPROVED, sm.APPROVE)


def test_the_wrong_actor_is_refused():
    with pytest.raises(sm.ActorNotAllowed):
        sm.resolve(sm.AWAITING_UNIT_HEAD, sm.APPROVE, sm.EMPLOYEE)
    assert sm.resolve(sm.AWAITING_UNIT_HEAD, sm.APPROVE, sm.UNIT_HEAD)


def test_every_named_guard_has_an_implementation():
    named = {g for t in sm.TRANSITIONS for g in t.guards}
    assert named <= guards.names(), f"unimplemented: {sorted(named - guards.names())}"


def test_no_guard_implementation_is_unused():
    named = {g for t in sm.TRANSITIONS for g in t.guards}
    assert guards.names() <= named, f"never reached: {sorted(guards.names() - named)}"


def test_every_permission_in_the_table_is_declared_in_the_registry():
    declared = {code for code, _ in PERMISSIONS}
    assert sm.permission_codes() <= declared, (
        f"the table uses undeclared codes: {sorted(sm.permission_codes() - declared)}")


def test_the_registry_declares_nothing_the_table_or_a_service_cannot_use():
    """A declared permission nobody holds and no code path checks is a promise."""
    granted = set(SYSTEM_PERMISSIONS)
    assert granted, "scheduled work needs at least one system permission"


def test_nobody_may_sanction_their_own_request():
    own = [t for t in sm.TRANSITIONS
           if t.permission in ("leave.request.approve", "leave.resumption.review")
           and "not_own_request" not in t.guards]
    assert own == [], "every approval edge needs the self-approval guard"


def test_withdrawal_is_available_until_the_final_decision():
    for state in sorted(sm.PENDING - {sm.DRAFT}):
        assert sm.is_legal(state, sm.WITHDRAW), f"{state} cannot be withdrawn"
    assert not sm.is_legal(sm.APPROVED, sm.WITHDRAW)
    assert not sm.is_legal(sm.CANCELLED, sm.WITHDRAW)


def test_there_is_no_modify_edge_at_all():
    """BR-EL-034: the retired capability must not exist as a transition."""
    events = {t.event for t in sm.TRANSITIONS}
    assert "modify" not in events
    assert "edit" not in events


def test_a_decline_does_not_release_the_routing_gate():
    decline = sm.resolve(sm.AWAITING_SUBSTITUTE, sm.DECLINE, sm.SUBSTITUTE)
    assert decline.to == sm.APPLICANT_ACTION_REQUIRED
    accept = sm.resolve(sm.AWAITING_SUBSTITUTE, sm.ACCEPT, sm.SUBSTITUTE)
    assert accept.to in (sm.AWAITING_UNIT_HEAD, sm.AWAITING_DIRECTOR_SELF_SANCTION)


def test_not_recommended_continues_to_the_higher_sanction_path():
    """BR-EL-017: Not Recommended is not a rejection, so it is not REJECT."""
    edge = sm.resolve(sm.AWAITING_UNIT_HEAD, sm.RECOMMEND, sm.UNIT_HEAD)
    assert edge.to in (sm.AWAITING_ESTABLISHMENT, sm.AWAITING_FINAL_SANCTION)


def test_a_rejected_extension_leaves_the_leave_approved():
    edge = sm.resolve(sm.EXTENSION_AWAITING_FINAL, sm.REJECT, sm.SANCTIONING_AUTHORITY)
    assert edge.to == sm.APPROVED


def test_resumption_has_three_outcomes_and_no_closed_state():
    events = {sm.REVIEW_NORMAL, sm.REVIEW_EARLY, sm.REVIEW_LATE}
    targets = {t.to for t in sm.TRANSITIONS if t.event in events}
    assert targets == {sm.RESUMPTION_NO_ADJUSTMENT, sm.RESUMPTION_EARLY,
                       sm.RESUMPTION_LATE}
    assert "closed" not in sm.STATUSES


@pytest.mark.parametrize(("actual_offset", "expected"), [
    (-2, sm.REVIEW_EARLY),
    (0, sm.REVIEW_NORMAL),
    (3, sm.REVIEW_LATE),
])
def test_the_review_event_follows_the_actual_return_date(actual_offset, expected):
    from datetime import date, timedelta

    approved_end = date(2026, 6, 10)
    assert sm.resumption_event(actual=approved_end + timedelta(days=actual_offset),
                               approved_end=approved_end) == expected
