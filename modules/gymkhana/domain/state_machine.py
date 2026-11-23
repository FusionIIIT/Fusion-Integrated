# Pure domain state machine transitions for Gymkhana

from modules.gymkhana.domain.constants import STATUS_CONFIRMED, STATUS_OPEN

CLUB_TRANSITIONS = {
    (STATUS_OPEN, "confirm"): STATUS_CONFIRMED,
}

MEMBERSHIP_TRANSITIONS = {
    (STATUS_OPEN, "approve"): STATUS_CONFIRMED,
}


def transition_club(current_status: str, event: str) -> str:
    key = (current_status, event)
    if key not in CLUB_TRANSITIONS:
        msg = f"Illegal club state transition from {current_status!r} on event {event!r}"
        raise ValueError(msg)
    return CLUB_TRANSITIONS[key]


def transition_membership(current_status: str, event: str) -> str:
    key = (current_status, event)
    if key not in MEMBERSHIP_TRANSITIONS:
        msg = f"Illegal membership transition from {current_status!r} on event {event!r}"
        raise ValueError(msg)
    return MEMBERSHIP_TRANSITIONS[key]
