"""Pure domain tests for ELM state machine (millisecond execution, zero DB dependency)."""
from __future__ import annotations

import pytest
from modules.elm.domain import state_machine as sm


def test_transition_table_is_authoritative():
    """Verify all transitions in TRANSITIONS are registered in _TRANSITION_MAP."""
    declared = {(t.frm, t.to) for t in sm.TRANSITIONS}
    for frm, to in declared:
        assert sm.is_legal_transition(frm, to) is True
        t = sm.get_transition(frm, to)
        assert t.frm == frm
        assert t.to == to


def test_illegal_transition_raises():
    """Moving directly from draft to approved or cancelled without review raises InvalidTransition."""
    with pytest.raises(sm.InvalidTransition):
        sm.get_transition(sm.DRAFT, sm.APPROVED)

    with pytest.raises(sm.InvalidTransition):
        sm.get_transition(sm.DRAFT, sm.CANCELLED)

    with pytest.raises(sm.InvalidTransition):
        sm.get_transition(sm.PENDING_SUBSTITUTE, sm.APPROVED)


def test_terminal_states_have_no_subsequent_forward_transitions():
    """Terminal states (Rejected, Withdrawn, Cancelled) have no further workflow progression."""
    assert sm.allowed_targets_from(sm.REJECTED) == []
    assert sm.allowed_targets_from(sm.WITHDRAWN) == []
    assert sm.allowed_targets_from(sm.CANCELLED) == []


def test_approved_allows_only_cancellation_request():
    """Approved leave can only transition to cancellation review."""
    targets = sm.allowed_targets_from(sm.APPROVED)
    assert targets == [sm.CANCELLATION_PENDING_UNIT_HEAD]


def test_substitute_consent_gate_transitions():
    """Substitute response transitions."""
    # Accept releases gate to Unit Head
    t_accept = sm.get_transition(sm.PENDING_SUBSTITUTE, sm.PENDING_UNIT_HEAD)
    assert sm.ACTOR_SUBSTITUTE in t_accept.allowed_actors
    assert sm.ACTOR_APPLICANT not in t_accept.allowed_actors

    # Decline transitions to substitute_declined
    t_decline = sm.get_transition(sm.PENDING_SUBSTITUTE, sm.SUBSTITUTE_DECLINED)
    assert sm.ACTOR_SUBSTITUTE in t_decline.allowed_actors

    # Replacement nomination transitions back to pending_substitute
    t_replace = sm.get_transition(sm.SUBSTITUTE_DECLINED, sm.PENDING_SUBSTITUTE)
    assert sm.ACTOR_APPLICANT in t_replace.allowed_actors


def test_applicant_cannot_approve_own_leave():
    """Applicant actor is strictly forbidden from executing approval transitions."""
    t_uh_approve = sm.get_transition(sm.PENDING_UNIT_HEAD, sm.APPROVED)
    with pytest.raises(sm.ActorNotAllowed):
        sm.check_actor(t_uh_approve, sm.ACTOR_APPLICANT)

    t_sanction_approve = sm.get_transition(sm.PENDING_SANCTION, sm.APPROVED)
    with pytest.raises(sm.ActorNotAllowed):
        sm.check_actor(t_sanction_approve, sm.ACTOR_APPLICANT)


def test_director_self_sanction_transitions():
    """Director applicant transitions to self-sanction and can self-approve per BR-EL-020."""
    t_dir_submit = sm.get_transition(sm.DRAFT, sm.AWAITING_DIRECTOR_SANCTION)
    assert "is_director" in t_dir_submit.guards

    t_dir_approve = sm.get_transition(sm.AWAITING_DIRECTOR_SANCTION, sm.APPROVED)
    assert sm.ACTOR_DIRECTOR in t_dir_approve.allowed_actors
    # Must succeed without ActorNotAllowed
    sm.check_actor(t_dir_approve, sm.ACTOR_DIRECTOR)

    t_dir_reject = sm.get_transition(sm.AWAITING_DIRECTOR_SANCTION, sm.REJECTED)
    assert sm.ACTOR_DIRECTOR in t_dir_reject.allowed_actors
    sm.check_actor(t_dir_reject, sm.ACTOR_DIRECTOR)


def test_immediate_withdrawal_from_all_in_flight_states():
    """Applicant can immediately withdraw pending requests from any in-flight state (BR-EL-022)."""
    in_flight_states = [
        sm.PENDING_SUBSTITUTE,
        sm.SUBSTITUTE_DECLINED,
        sm.PENDING_UNIT_HEAD,
        sm.PENDING_SANCTION,
        sm.AWAITING_DIRECTOR_SANCTION,
        sm.SUBMITTED_LEGACY,
    ]
    for state in in_flight_states:
        t = sm.get_transition(state, sm.WITHDRAWN)
        assert sm.ACTOR_APPLICANT in t.allowed_actors
        sm.check_actor(t, sm.ACTOR_APPLICANT)


def test_approved_cancellation_hierarchy():
    """Cancellation transitions follow Unit Head (for CL/RH) or Higher Sanction path."""
    # CL/RH path: Unit Head approve -> Cancelled; reject -> Approved
    t_uh_cancel_app = sm.get_transition(sm.CANCELLATION_PENDING_UNIT_HEAD, sm.CANCELLED)
    assert sm.ACTOR_UNIT_HEAD in t_uh_cancel_app.allowed_actors

    t_uh_cancel_rej = sm.get_transition(sm.CANCELLATION_PENDING_UNIT_HEAD, sm.APPROVED)
    assert sm.ACTOR_UNIT_HEAD in t_uh_cancel_rej.allowed_actors

    # Higher Sanction path: Unit Head recommends -> Sanctioning Authority decides
    t_uh_cancel_rec = sm.get_transition(sm.CANCELLATION_PENDING_UNIT_HEAD, sm.CANCELLATION_PENDING_SANCTION)
    assert sm.ACTOR_UNIT_HEAD in t_uh_cancel_rec.allowed_actors

    t_sanc_cancel_app = sm.get_transition(sm.CANCEATION_PENDING_SANCTION if hasattr(sm, 'CANCEATION_PENDING_SANCTION') else sm.CANCELLATION_PENDING_SANCTION, sm.CANCELLED)
    assert sm.ACTOR_SANCTIONING_AUTHORITY in t_sanc_cancel_app.allowed_actors

    t_sanc_cancel_rej = sm.get_transition(sm.CANCELLATION_PENDING_SANCTION, sm.APPROVED)
    assert sm.ACTOR_SANCTIONING_AUTHORITY in t_sanc_cancel_rej.allowed_actors
