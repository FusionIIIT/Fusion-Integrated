import itertools

import pytest

from modules.vms.domain import request_state as rs

ALL_FLAG_COMBOS = [dict(zip(rs.FLAGS, v)) for v in itertools.product([False, True], repeat=3)]


@pytest.mark.parametrize("t", rs.TABLE, ids=lambda t: f"{t.kind}:{t.frm}:{t.event}:{t.actor}:{t.to}")
def test_every_row_resolves_to_itself(t):
    flags = dict(t.when)
    assert rs.resolve(t.kind, t.frm, t.event, t.actor, flags) == t
    assert rs.next_state(t.kind, t.frm, t.event, t.actor, flags) == t.to


def test_no_flag_combination_is_ambiguous():
    keys = {(t.kind, t.frm, t.event, t.actor) for t in rs.TABLE}
    for key in keys:
        for flags in ALL_FLAG_COMBOS:
            try:
                rs.resolve(*key, flags)
            except rs.InvalidTransition:
                pass  # a guard excluded it; fine


def test_every_state_and_event_is_used():
    assert {t.to for t in rs.TABLE} >= set(rs.STATES)
    assert {t.event for t in rs.TABLE} == set(rs.EVENTS)
    assert {t.actor for t in rs.TABLE} <= set(rs.ACTORS)


def test_cancelled_is_not_a_state():  # D-4
    assert "cancelled" not in rs.STATES


# --- the named workflows, end to end ---------------------------------------------------
def walk(kind, steps):
    state = rs.NOT_SUBMITTED
    for event, actor, flags in steps:
        state = rs.next_state(kind, state, event, actor, flags)
    return state


def test_bw_vms_01_approved_visit():
    assert walk(rs.PRE_REGISTERED, [(rs.SUBMIT, rs.VISITOR, {}), (rs.HOST_APPROVE, rs.HOST, {}),
                                    (rs.COMPLETE, rs.SECURITY, {})]) == rs.COMPLETED


def test_bw_vms_02_rejected_visit():
    assert walk(rs.PRE_REGISTERED, [(rs.SUBMIT, rs.VISITOR, {}),
                                    (rs.HOST_REJECT, rs.HOST, {})]) == rs.REJECTED


def test_bw_vms_03_timeout():
    assert walk(rs.PRE_REGISTERED, [(rs.SUBMIT, rs.VISITOR, {}),
                                    (rs.AUTO_EXPIRE, rs.SYSTEM, {})]) == rs.EXPIRED


def test_bw_vms_06_walkin_host_approved():
    assert walk(rs.WALK_IN, [(rs.SUBMIT, rs.SECURITY, {"host_available": True}),
                             (rs.HOST_APPROVE, rs.HOST, {}),
                             (rs.COMPLETE, rs.SECURITY, {})]) == rs.COMPLETED


def test_bw_vms_07_walkin_contingency():
    assert rs.next_state(rs.WALK_IN, rs.NOT_SUBMITTED, rs.SUBMIT, rs.SECURITY,
                         {"host_available": False}) == rs.AWAITING_ADMIN
    assert walk(rs.WALK_IN, [(rs.SUBMIT, rs.SECURITY, {"host_available": False}),
                             (rs.ADMIN_APPROVE_CONTINGENCY, rs.ADMIN, {}),
                             (rs.COMPLETE, rs.SYSTEM, {})]) == rs.COMPLETED


def test_walkin_contingency_reject():
    assert walk(rs.WALK_IN, [(rs.SUBMIT, rs.SECURITY, {}),
                             (rs.ADMIN_REJECT_CONTINGENCY, rs.ADMIN, {})]) == rs.REJECTED


def test_bw_vms_08_walkin_host_rejected():
    assert walk(rs.WALK_IN, [(rs.SUBMIT, rs.SECURITY, {"host_available": True}),
                             (rs.HOST_REJECT, rs.HOST, {})]) == rs.REJECTED


def test_bw_vms_22_urgent_goes_through_admin_then_host():
    assert walk(rs.PRE_REGISTERED, [(rs.SUBMIT, rs.VISITOR, {"urgent": True}),
                                    (rs.URGENT_APPROVE, rs.ADMIN, {}),
                                    (rs.HOST_APPROVE, rs.HOST, {}),
                                    (rs.COMPLETE, rs.SECURITY, {})]) == rs.COMPLETED


def test_bw_vms_22_urgent_reject():
    assert walk(rs.PRE_REGISTERED, [(rs.SUBMIT, rs.VISITOR, {"urgent": True}),
                                    (rs.URGENT_REJECT, rs.ADMIN, {})]) == rs.REJECTED


def test_preauth_or_vip_bypass_skips_host_approval():  # BR-195/197; also beats urgent (BR-203)
    for flags in ({"bypass_approval": True}, {"bypass_approval": True, "urgent": True}):
        assert rs.next_state(rs.PRE_REGISTERED, rs.NOT_SUBMITTED, rs.SUBMIT, rs.VISITOR,
                             flags) == rs.APPROVED


# --- illegal moves ----------------------------------------------------------------------
@pytest.mark.parametrize("kind", rs.KINDS)
@pytest.mark.parametrize("state", rs.STATES)
def test_illegal_move_per_state(kind, state):
    legal = {(t.event, t.actor) for t in rs.TABLE if t.kind == kind and t.frm == state}
    illegal = [(e, a) for e in rs.EVENTS for a in rs.ACTORS if (e, a) not in legal]
    assert illegal
    for event, actor in illegal:
        with pytest.raises(rs.InvalidTransition):
            rs.resolve(kind, state, event, actor, {"urgent": True, "host_available": True})


@pytest.mark.parametrize("kind", rs.KINDS)
@pytest.mark.parametrize("state", sorted(rs.TERMINAL))
def test_terminal_states_have_no_exit(kind, state):
    assert rs.legal_events(kind, state) == frozenset()


def test_wrong_actor_rejected():
    with pytest.raises(rs.InvalidTransition):
        rs.resolve(rs.PRE_REGISTERED, rs.PENDING, rs.HOST_APPROVE, rs.VISITOR)


def test_walk_in_cannot_use_urgent_events_and_vice_versa():
    with pytest.raises(rs.InvalidTransition):
        rs.resolve(rs.WALK_IN, rs.AWAITING_ADMIN, rs.URGENT_APPROVE, rs.ADMIN)
    with pytest.raises(rs.InvalidTransition):
        rs.resolve(rs.PRE_REGISTERED, rs.AWAITING_ADMIN, rs.ADMIN_APPROVE_CONTINGENCY, rs.ADMIN)


def test_legal_events():
    assert rs.legal_events(rs.PRE_REGISTERED, rs.PENDING, rs.HOST) == {rs.HOST_APPROVE, rs.HOST_REJECT}
    assert rs.legal_events(rs.PRE_REGISTERED, rs.PENDING) == {
        rs.HOST_APPROVE, rs.HOST_REJECT, rs.AUTO_EXPIRE}
