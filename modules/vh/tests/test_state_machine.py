# State machine unit tests: Exhaustive transition coverage.
import pytest

from modules.vh.domain.state_machine import (
    PRE_ARRIVAL_STATES,
    TERMINAL_STATES,
    TRANSITIONS,
    InvalidStateTransitionError,
    can_allot_rooms,
    can_cancel_booking,
    can_checkin,
    can_checkout,
    can_modify_booking,
    transition,
)

ALL_STATES = [
    "pending",
    "pending_offline",
    "forwarded",
    "forwarded_offline",
    "approved",
    "approved_offline",
    "rejected",
    "rejected_offline",
    "room_allotted",
    "checked_in",
    "checked_out",
    "cancellation_requested",
    "cancelled",
]

ALL_EVENTS = [
    "caretaker_reject",
    "caretaker_forward",
    "incharge_approve",
    "incharge_reject",
    "allot_room",
    "check_in",
    "check_out",
    "request_cancellation",
    "confirm_cancellation",
]

ALL_ROLES = ["indenter", "caretaker", "incharge"]


def test_all_declared_transitions_succeed():
    # BW-VH-01 through BW-VH-10: Verifies every declared transition in the matrix
    for (state, event, role), expected in TRANSITIONS.items():
        assert transition(state, event, role) == expected


def test_illegal_transitions_are_refused():
    # Ensures inexpressible transitions raise InvalidStateTransitionError
    declared = set(TRANSITIONS.keys())
    for s in ALL_STATES:
        for e in ALL_EVENTS:
            for r in ALL_ROLES:
                if (s, e, r) not in declared:
                    with pytest.raises(InvalidStateTransitionError):
                        transition(s, e, r)


def test_terminal_states_cannot_transition():
    # Terminal states reject all outbound events
    for s in TERMINAL_STATES:
        for e in ALL_EVENTS:
            for r in ALL_ROLES:
                with pytest.raises(InvalidStateTransitionError):
                    transition(s, e, r)


def test_pre_arrival_and_operational_predicates():
    # BR-VH-012: Allotment allowed only after approval
    assert can_allot_rooms("approved") is True
    assert can_allot_rooms("approved_offline") is True
    assert can_allot_rooms("pending") is False
    assert can_allot_rooms("room_allotted") is False

    # Checkin allowed only when room is allotted
    assert can_checkin("room_allotted") is True
    assert can_checkin("approved") is False
    assert can_checkin("checked_in") is False

    # Checkout allowed only when checked in
    assert can_checkout("checked_in") is True
    assert can_checkout("room_allotted") is False

    # Pre-arrival cancellation and modification
    for s in PRE_ARRIVAL_STATES:
        assert can_cancel_booking(s) is True
    assert can_cancel_booking("checked_in") is False
    assert can_cancel_booking("checked_out") is False
    assert can_modify_booking("pending") is True
    assert can_modify_booking("checked_in") is False
