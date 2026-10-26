"""The transition table against the STTs; every illegal move enumerated, not hand-picked."""
import itertools

import pytest

from modules.leave.domain import state_machine as sm

ALL_STATES = [sm.DRAFT, *sorted(sm.PENDING), *sorted(sm.TERMINAL)]
ALL_EVENTS = [sm.SUBMIT, sm.SUBSTITUTE_ACCEPT, sm.SUBSTITUTE_DECLINE, sm.RENOMINATE,
              sm.UNIT_HEAD_APPROVE, sm.UNIT_HEAD_REJECT, sm.UNIT_HEAD_RECOMMEND,
              sm.ESTABLISHMENT_FORWARD, sm.SANCTION_APPROVE, sm.SANCTION_REJECT, sm.WITHDRAW]
ACTORS = [sm.EMPLOYEE, sm.SUBSTITUTE, sm.UNIT_HEAD, sm.ESTABLISHMENT, sm.AUTHORITY, sm.DIRECTOR]
FLAG_SETS = [dict(zip(sm.FLAGS, values, strict=True))
             for values in itertools.product([False, True], repeat=len(sm.FLAGS))]


def test_every_row_resolves_to_exactly_itself():
    for t in sm.TRANSITIONS:
        flags = dict(t.when)
        assert sm.resolve(t.kind, t.frm, t.event, t.actor, flags) == t


def test_no_flag_combination_is_ambiguous():
    for kind, frm, event, actor in itertools.product(sm.KINDS, ALL_STATES, ALL_EVENTS, ACTORS):
        for flags in FLAG_SETS:
            matching = [t for t in sm.candidates(kind, frm, event, actor) if t.matches(flags)]
            assert len(matching) <= 1, (kind, frm, event, actor, flags)


@pytest.mark.parametrize("kind", sm.KINDS)
def test_every_unlisted_move_is_refused(kind):
    listed = {(t.frm, t.event, t.actor) for t in sm.TRANSITIONS if t.kind == kind}
    for frm, event, actor in itertools.product(ALL_STATES, ALL_EVENTS, ACTORS):
        if (frm, event, actor) in listed:
            continue
        with pytest.raises(sm.InvalidTransition):
            sm.resolve(kind, frm, event, actor, {})


def test_nothing_leaves_a_terminal_state():
    assert not [t for t in sm.TRANSITIONS if t.frm in sm.TERMINAL]


def test_cl_rh_unit_head_is_final_and_cannot_recommend():
    assert sm.resolve(sm.NEW, sm.AWAITING_UNIT_HEAD, sm.UNIT_HEAD_APPROVE, sm.UNIT_HEAD,
                      {"uh_final": True}).to == sm.APPROVED
    with pytest.raises(sm.InvalidTransition):
        sm.resolve(sm.NEW, sm.AWAITING_UNIT_HEAD, sm.UNIT_HEAD_RECOMMEND, sm.UNIT_HEAD,
                   {"uh_final": True})


def test_higher_sanction_unit_head_cannot_decide():
    """BR-EL-017: Not Recommended is never a rejection, and the Unit Head never approves."""
    for event in (sm.UNIT_HEAD_APPROVE, sm.UNIT_HEAD_REJECT):
        with pytest.raises(sm.InvalidTransition):
            sm.resolve(sm.NEW, sm.AWAITING_UNIT_HEAD, event, sm.UNIT_HEAD, {"uh_final": False})


@pytest.mark.parametrize("estt,to", [(True, sm.AWAITING_ESTABLISHMENT),
                                     (False, sm.AWAITING_SANCTION)])
def test_establishment_step_only_where_configured(estt, to):
    assert sm.resolve(sm.NEW, sm.AWAITING_UNIT_HEAD, sm.UNIT_HEAD_RECOMMEND, sm.UNIT_HEAD,
                      {"uh_final": False, "establishment": estt}).to == to


def test_substitute_gate_holds_routing():
    """BR-EL-015: from awaiting_substitute only the substitute's answer or withdrawal moves it."""
    events = {t.event for t in sm.TRANSITIONS if t.frm == sm.AWAITING_SUBSTITUTE}
    assert events == {sm.SUBSTITUTE_ACCEPT, sm.SUBSTITUTE_DECLINE, sm.WITHDRAW}


def test_director_route_skips_unit_head():
    assert sm.resolve(sm.NEW, sm.DRAFT, sm.SUBMIT, sm.EMPLOYEE,
                      {"director": True}).to == sm.AWAITING_DIRECTOR
    assert sm.resolve(sm.NEW, sm.AWAITING_SUBSTITUTE, sm.SUBSTITUTE_ACCEPT, sm.SUBSTITUTE,
                      {"director": True}).to == sm.AWAITING_DIRECTOR


def test_withdrawal_from_every_pending_new_state():
    for state in sm.PENDING:
        assert sm.resolve(sm.NEW, state, sm.WITHDRAW, sm.EMPLOYEE).to == sm.WITHDRAWN


def test_cancellation_cannot_be_withdrawn_or_take_a_substitute():
    """CW-EL-02 has neither row."""
    assert not [t for t in sm.TRANSITIONS
                if t.kind == sm.CANCELLATION and t.event in (sm.WITHDRAW, sm.SUBSTITUTE_ACCEPT)]


def test_extension_has_no_unit_head_final_decision():
    assert not [t for t in sm.TRANSITIONS
                if t.kind == sm.EXTENSION and t.event in (sm.UNIT_HEAD_APPROVE,
                                                          sm.UNIT_HEAD_REJECT)]


def test_unknown_flag_is_a_programming_error():
    with pytest.raises(ValueError):
        sm.resolve(sm.NEW, sm.DRAFT, sm.SUBMIT, sm.EMPLOYEE, {"vip": True})
