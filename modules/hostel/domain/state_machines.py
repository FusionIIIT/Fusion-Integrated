"""State machines and pure transitions for Hostel Management.

Imports no Django, no DRF, no Celery. Pure Python.
"""

# Transition table mapping (current_state, event, role) -> next_state
LEAVE_TRANSITIONS: dict[tuple[str, str, str], str] = {
    ("PENDING", "approve", "caretaker"): "APPROVED",
    ("PENDING", "reject", "caretaker"): "REJECTED",
    ("PENDING", "cancel", "student"): "CANCELLED",
}

COMPLAINT_TRANSITIONS: dict[tuple[str, str, str], str] = {
    ("LOGGED", "start_review", "caretaker"): "IN_PROGRESS",
    ("IN_PROGRESS", "escalate", "caretaker"): "ESCALATED",
    ("IN_PROGRESS", "resolve", "caretaker"): "RESOLVED",
    ("ESCALATED", "resolve", "warden"): "RESOLVED",
    ("RESOLVED", "close", "student"): "CLOSED",
}

GUEST_ROOM_TRANSITIONS: dict[tuple[str, str, str], str] = {
    ("REQUESTED", "approve", "caretaker"): "APPROVED",
    ("REQUESTED", "reject", "caretaker"): "REJECTED",
    ("REQUESTED", "cancel", "student"): "CANCELLED",
}

EXTENDED_STAY_TRANSITIONS: dict[tuple[str, str, str], str] = {
    ("SUBMITTED", "approve", "warden"): "APPROVED",
    ("SUBMITTED", "reject", "warden"): "REJECTED",
}


class InvalidTransitionError(Exception):
    def __init__(self, current_state: str, event: str, role: str):
        super().__init__(
            f"Cannot apply event '{event}' by role '{role}' from state '{current_state}'."
        )
        self.current_state = current_state
        self.event = event
        self.role = role


def apply_leave_transition(current_state: str, event: str, role: str) -> str:
    key = (current_state, event, role)
    if key not in LEAVE_TRANSITIONS:
        raise InvalidTransitionError(current_state, event, role)
    return LEAVE_TRANSITIONS[key]


def apply_complaint_transition(current_state: str, event: str, role: str) -> str:
    key = (current_state, event, role)
    if key not in COMPLAINT_TRANSITIONS:
        raise InvalidTransitionError(current_state, event, role)
    return COMPLAINT_TRANSITIONS[key]


def apply_guest_room_transition(current_state: str, event: str, role: str) -> str:
    key = (current_state, event, role)
    if key not in GUEST_ROOM_TRANSITIONS:
        raise InvalidTransitionError(current_state, event, role)
    return GUEST_ROOM_TRANSITIONS[key]


def apply_extended_stay_transition(current_state: str, event: str, role: str) -> str:
    key = (current_state, event, role)
    if key not in EXTENDED_STAY_TRANSITIONS:
        raise InvalidTransitionError(current_state, event, role)
    return EXTENDED_STAY_TRANSITIONS[key]
