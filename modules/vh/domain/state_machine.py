# Pure Python state machine for VHMS booking and stay progression.


class InvalidStateTransitionError(ValueError):
    # Raised when an invalid state transition is requested.
    pass


# Declarative transition table: (current_state, event, actor_role) -> resulting_state
TRANSITIONS: dict[tuple[str, str, str], str] = {
    # Online booking paths (BW-VH-01, BW-VH-02, BW-VH-03)
    ("pending", "caretaker_reject", "caretaker"): "rejected",
    ("pending", "caretaker_forward", "caretaker"): "forwarded",
    ("forwarded", "incharge_approve", "incharge"): "approved",
    ("forwarded", "incharge_reject", "incharge"): "rejected",
    # Offline booking paths (BW-VH-04, BW-VH-05, BW-VH-06)
    ("pending_offline", "caretaker_reject", "caretaker"): "rejected",
    ("pending_offline", "caretaker_forward", "caretaker"): "forwarded_offline",
    ("forwarded_offline", "incharge_approve", "incharge"): "approved_offline",
    ("forwarded_offline", "incharge_reject", "incharge"): "rejected_offline",
    # Stay paths (BW-VH-10)
    ("approved", "allot_room", "caretaker"): "room_allotted",
    ("approved_offline", "allot_room", "caretaker"): "room_allotted",
    ("room_allotted", "check_in", "caretaker"): "checked_in",
    ("checked_in", "check_out", "caretaker"): "checked_out",
    # Cancellation paths (BW-VH-07, BW-VH-08, BW-VH-09, CW-VH-02)
    ("pending", "request_cancellation", "indenter"): "cancellation_requested",
    ("forwarded", "request_cancellation", "indenter"): "cancellation_requested",
    ("approved", "request_cancellation", "indenter"): "cancellation_requested",
    ("room_allotted", "request_cancellation", "indenter"): "cancellation_requested",
    ("cancellation_requested", "confirm_cancellation", "caretaker"): "cancelled",
}

TERMINAL_STATES = frozenset({"rejected", "rejected_offline", "cancelled", "checked_out"})
PRE_ARRIVAL_STATES = frozenset(
    {
        "pending",
        "pending_offline",
        "forwarded",
        "forwarded_offline",
        "approved",
        "approved_offline",
        "room_allotted",
    }
)


def transition(current_state: str, event: str, actor_role: str) -> str:
    # Computes resulting state or raises InvalidStateTransitionError.
    key = (current_state.lower(), event.lower(), actor_role.lower())
    if key not in TRANSITIONS:
        msg = f"Transition not allowed: state '{current_state}', event '{event}'."
        raise InvalidStateTransitionError(msg)
    return TRANSITIONS[key]


def can_modify_booking(status: str) -> bool:
    # Returns True if booking can be modified before arrival.
    return status.lower() in PRE_ARRIVAL_STATES and status.lower() != "cancellation_requested"


def can_cancel_booking(status: str) -> bool:
    # Returns True if booking can be requested for cancellation before arrival.
    return status.lower() in PRE_ARRIVAL_STATES


def can_allot_rooms(status: str) -> bool:
    # BR-VH-012: Room allotment permitted only after booking approval.
    return status.lower() in {"approved", "approved_offline"}


def can_checkin(status: str) -> bool:
    # Check-in permitted only when room is allotted.
    return status.lower() == "room_allotted"


def can_checkout(status: str) -> bool:
    # Check-out permitted only when currently checked in.
    return status.lower() == "checked_in"
