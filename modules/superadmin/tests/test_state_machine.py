"""State machine tests: exhaustive state-transition matrix checks for all 3 lifecycles."""

import pytest

from modules.superadmin.domain.exceptions import InvalidStateTransitionError
from modules.superadmin.domain.state_machine import (
    PURGE_TERMINAL_STATES,
    PURGE_TRANSITIONS,
    ROLE_TERMINAL_STATES,
    ROLE_TRANSITIONS,
    USER_TERMINAL_STATES,
    USER_TRANSITIONS,
    is_legal_purge_transition,
    is_legal_role_transition,
    is_legal_user_transition,
    resolve_purge_transition,
    resolve_role_transition,
    resolve_user_transition,
)

ALL_USER_STATES = ["ACTIVE", "DEACTIVATED", "ARCHIVED_REVERSIBLE", "ARCHIVED_PERMANENT"]
ALL_ROLE_STATES = ["SCHEDULED", "ACTIVE", "EXPIRED", "REVOKED"]
ALL_PURGE_STATES = ["REQUESTED", "AUTHORIZED", "REJECTED", "PURGED"]


# ==========================================
# 1. User Lifecycle State Machine (BW-SA-08)
# ==========================================


def test_user_lifecycle_exhaustive_matrix():
    declared = {(t.from_state, t.to_state) for t in USER_TRANSITIONS}
    for frm in ALL_USER_STATES:
        for to in ALL_USER_STATES:
            assert is_legal_user_transition(frm, to) is ((frm, to) in declared)


def test_user_terminal_state_has_no_exits():
    for s in USER_TERMINAL_STATES:
        for target in ALL_USER_STATES:
            assert is_legal_user_transition(s, target) is False
            with pytest.raises(InvalidStateTransitionError):
                resolve_user_transition(s, target)


def test_user_legal_transitions_resolve_successfully():
    # Active -> Deactivated
    t1 = resolve_user_transition("ACTIVE", "DEACTIVATED")
    assert t1.to_state == "DEACTIVATED"

    # Deactivated -> Active (Reactivation)
    t2 = resolve_user_transition("DEACTIVATED", "ACTIVE")
    assert t2.to_state == "ACTIVE"

    # Deactivated -> Archived Reversible (Transition 1 of BW-SA-08)
    t3 = resolve_user_transition("DEACTIVATED", "ARCHIVED_REVERSIBLE")
    assert t3.to_state == "ARCHIVED_REVERSIBLE"

    # Archived Reversible -> Active (Restoration)
    t4 = resolve_user_transition("ARCHIVED_REVERSIBLE", "ACTIVE")
    assert t4.to_state == "ACTIVE"

    # Archived Reversible -> Archived Permanent (Transition 2 of BW-SA-08)
    t5 = resolve_user_transition("ARCHIVED_REVERSIBLE", "ARCHIVED_PERMANENT")
    assert t5.to_state == "ARCHIVED_PERMANENT"


def test_user_illegal_shortcuts_raise():
    # Cannot jump straight from ACTIVE to ARCHIVED_REVERSIBLE
    with pytest.raises(
        InvalidStateTransitionError, match="Cannot move from 'ACTIVE' to 'ARCHIVED_REVERSIBLE'"
    ):
        resolve_user_transition("ACTIVE", "ARCHIVED_REVERSIBLE")

    # Cannot jump straight from ACTIVE to ARCHIVED_PERMANENT
    with pytest.raises(
        InvalidStateTransitionError, match="Cannot move from 'ACTIVE' to 'ARCHIVED_PERMANENT'"
    ):
        resolve_user_transition("ACTIVE", "ARCHIVED_PERMANENT")

    # Cannot restore an ARCHIVED_PERMANENT user
    with pytest.raises(
        InvalidStateTransitionError, match="Cannot move from 'ARCHIVED_PERMANENT' to 'ACTIVE'"
    ):
        resolve_user_transition("ARCHIVED_PERMANENT", "ACTIVE")


# ==========================================
# 2. Role Lifecycle State Machine
# ==========================================


def test_role_lifecycle_exhaustive_matrix():
    declared = {(t.from_state, t.to_state) for t in ROLE_TRANSITIONS}
    for frm in ALL_ROLE_STATES:
        for to in ALL_ROLE_STATES:
            assert is_legal_role_transition(frm, to) is ((frm, to) in declared)


def test_role_terminal_states_have_no_exits():
    for s in ROLE_TERMINAL_STATES:
        for target in ALL_ROLE_STATES:
            assert is_legal_role_transition(s, target) is False
            with pytest.raises(InvalidStateTransitionError):
                resolve_role_transition(s, target)


def test_role_transitions_resolve_correctly():
    assert resolve_role_transition("SCHEDULED", "ACTIVE").to_state == "ACTIVE"
    assert resolve_role_transition("SCHEDULED", "REVOKED").to_state == "REVOKED"
    assert resolve_role_transition("ACTIVE", "EXPIRED").to_state == "EXPIRED"
    assert resolve_role_transition("ACTIVE", "REVOKED").to_state == "REVOKED"


# ==========================================
# 3. Purge Lifecycle State Machine
# ==========================================


def test_purge_lifecycle_exhaustive_matrix():
    declared = {(t.from_state, t.to_state) for t in PURGE_TRANSITIONS}
    for frm in ALL_PURGE_STATES:
        for to in ALL_PURGE_STATES:
            assert is_legal_purge_transition(frm, to) is ((frm, to) in declared)


def test_purge_terminal_states_have_no_exits():
    for s in PURGE_TERMINAL_STATES:
        for target in ALL_PURGE_STATES:
            assert is_legal_purge_transition(s, target) is False
            with pytest.raises(InvalidStateTransitionError):
                resolve_purge_transition(s, target)


def test_purge_transitions_resolve_correctly():
    assert resolve_purge_transition("REQUESTED", "AUTHORIZED").to_state == "AUTHORIZED"
    assert resolve_purge_transition("REQUESTED", "REJECTED").to_state == "REJECTED"
    assert resolve_purge_transition("AUTHORIZED", "PURGED").to_state == "PURGED"
