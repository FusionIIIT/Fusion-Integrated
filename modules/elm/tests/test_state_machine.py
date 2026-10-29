"""Tests for modules.elm.domain.state_machine -- pure Python, no DB.

Verifies CW-EL-01, CW-EL-02, CW-EL-03, and CW-EL-04 state transitions,
actor permission enforcement, and guard registration.
"""
import pytest

from modules.elm.domain import state_machine as sm


ALL_STATES = [
    sm.DRAFT,
    sm.AWAITING_SUBSTITUTE,
    sm.AWAITING_UNIT_HEAD,
    sm.AWAITING_ESTABLISHMENT,
    sm.AWAITING_SANCTION,
    sm.APPROVED,
    sm.REJECTED,
    sm.WITHDRAWN,
    sm.ONGOING,
    sm.CANCEL_REQUESTED,
    sm.CANCELLED,
    sm.EXTENSION_REQUESTED,
    sm.EXTENSION_APPROVED,
    sm.RESUMPTION_SUBMITTED,
    sm.RESUMPTION_REVIEWED,
]


def test_transition_table_is_specification():
    """All registered transitions match declared (frm, to)."""
    declared = {(t.frm, t.to) for t in sm.TRANSITIONS}
    for frm in ALL_STATES:
        for to in ALL_STATES:
            assert sm.is_legal(frm, to) is ((frm, to) in declared)


def test_terminal_states_have_no_exits():
    """Terminal states (REJECTED, WITHDRAWN, CANCELLED) cannot transition anywhere."""
    for s in sm.TERMINAL:
        assert sm.allowed_targets(s) == []


def test_illegal_transition_raises():
    """Direct jump from draft to ongoing or approved without approval is illegal."""
    with pytest.raises(sm.InvalidTransition):
        sm.resolve(sm.DRAFT, sm.ONGOING)

    with pytest.raises(sm.InvalidTransition):
        sm.resolve(sm.REJECTED, sm.APPROVED)

    with pytest.raises(sm.InvalidTransition):
        sm.resolve(sm.CANCELLED, sm.DRAFT)


def test_actor_not_allowed_raises():
    """An employee cannot approve leave directly."""
    with pytest.raises(sm.ActorNotAllowed):
        sm.resolve(sm.AWAITING_UNIT_HEAD, sm.APPROVED, actor_kind=sm.EMPLOYEE)

    with pytest.raises(sm.ActorNotAllowed):
        sm.resolve(sm.AWAITING_SANCTION, sm.APPROVED, actor_kind=sm.SUBSTITUTE)


def test_cw_el_01_new_leave_workflow_transitions():
    """Verify standard happy paths for leave application (CW-EL-01)."""
    # 1. Employee submits with substitute needed
    t1 = sm.resolve(sm.DRAFT, sm.AWAITING_SUBSTITUTE, actor_kind=sm.EMPLOYEE)
    assert "substitute_required" in t1.guards
    assert t1.permission == "elm.leave.apply"

    # 2. Substitute accepts
    t2 = sm.resolve(sm.AWAITING_SUBSTITUTE, sm.AWAITING_UNIT_HEAD, actor_kind=sm.SUBSTITUTE)
    assert "substitute_accepted" in t2.guards

    # 3. Unit head recommends to sanction authority
    t3 = sm.resolve(sm.AWAITING_UNIT_HEAD, sm.AWAITING_SANCTION, actor_kind=sm.UNIT_HEAD)
    assert "higher_sanction" in t3.guards

    # 4. Sanction authority approves
    t4 = sm.resolve(sm.AWAITING_SANCTION, sm.APPROVED, actor_kind=sm.SANCTION_AUTH)
    assert t4.permission == "elm.leave.approve"


def test_cw_el_01_substitute_decline_returns_to_draft():
    """When substitute declines, request returns to draft for re-nomination (BR-EL-015)."""
    t = sm.resolve(sm.AWAITING_SUBSTITUTE, sm.DRAFT, actor_kind=sm.SUBSTITUTE)
    assert "substitute_declined" in t.guards


def test_cw_el_01_cl_rh_direct_approval():
    """Unit head can approve CL/RH directly (BR-EL-016)."""
    t = sm.resolve(sm.AWAITING_UNIT_HEAD, sm.APPROVED, actor_kind=sm.UNIT_HEAD)
    assert "cl_or_rh" in t.guards


def test_cw_el_01_withdrawal():
    """Employee may withdraw request before approval."""
    for state in (sm.DRAFT, sm.AWAITING_SUBSTITUTE, sm.AWAITING_UNIT_HEAD, sm.AWAITING_SANCTION):
        t = sm.resolve(state, sm.WITHDRAWN, actor_kind=sm.EMPLOYEE)
        assert t.permission == "elm.leave.cancel"


def test_cw_el_02_cancellation():
    """Approved leave before start date can be requested for cancellation (CW-EL-02)."""
    t1 = sm.resolve(sm.APPROVED, sm.CANCEL_REQUESTED, actor_kind=sm.EMPLOYEE)
    assert "before_start_date" in t1.guards

    # Sanctioning authority confirms cancellation
    t2 = sm.resolve(sm.CANCEL_REQUESTED, sm.CANCELLED, actor_kind=sm.SANCTION_AUTH)
    assert t2.permission == "elm.leave.approve"

    # Or rejects cancellation request, restoring approved
    t3 = sm.resolve(sm.CANCEL_REQUESTED, sm.APPROVED, actor_kind=sm.SANCTION_AUTH)
    assert "has_reason" in t3.guards


def test_cw_el_03_extension():
    """Ongoing leave can be extended for EL/COL/VL (CW-EL-03)."""
    t1 = sm.resolve(sm.ONGOING, sm.EXTENSION_REQUESTED, actor_kind=sm.EMPLOYEE)
    assert "extendable_category" in t1.guards

    t2 = sm.resolve(sm.EXTENSION_REQUESTED, sm.EXTENSION_APPROVED, actor_kind=sm.SANCTION_AUTH)
    assert "extension_validated" in t2.guards


def test_cw_el_04_resumption():
    """Ongoing leave can submit resumption / early return (CW-EL-04)."""
    t1 = sm.resolve(sm.ONGOING, sm.RESUMPTION_SUBMITTED, actor_kind=sm.EMPLOYEE)
    assert "resumable_category" in t1.guards

    t2 = sm.resolve(sm.RESUMPTION_SUBMITTED, sm.RESUMPTION_REVIEWED, actor_kind=sm.SANCTION_AUTH)
    assert "resumption_verified" in t2.guards


def test_allowed_targets_by_actor():
    """Querying allowed targets returns only valid moves for that actor."""
    employee_draft_targets = sm.allowed_targets(sm.DRAFT, actor_kind=sm.EMPLOYEE)
    assert sm.AWAITING_SUBSTITUTE in employee_draft_targets
    assert sm.AWAITING_UNIT_HEAD in employee_draft_targets
    assert sm.WITHDRAWN in employee_draft_targets
    assert sm.APPROVED not in employee_draft_targets
