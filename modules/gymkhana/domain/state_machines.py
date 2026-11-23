"""Declarative state machine transition rules for Gymkhana."""

from __future__ import annotations

from modules.gymkhana.domain.constants import (
    CLUB_STATUS_CONFIRMED,
    CLUB_STATUS_OPEN,
    MEMBERSHIP_STATUS_CONFIRMED,
    MEMBERSHIP_STATUS_OPEN,
    POLL_STATUS_ACTIVE,
    POLL_STATUS_EXPIRED,
)
from modules.gymkhana.domain.exceptions import DomainStateError

# (current_state, event, actor_role) -> next_state
CLUB_TRANSITIONS = {
    (CLUB_STATUS_OPEN, "CONFIRM", "student_admin"): CLUB_STATUS_CONFIRMED,
}

MEMBERSHIP_TRANSITIONS = {
    (MEMBERSHIP_STATUS_OPEN, "APPROVE", "club_head"): MEMBERSHIP_STATUS_CONFIRMED,
}

POLL_TRANSITIONS = {
    (POLL_STATUS_ACTIVE, "EXPIRE", "system"): POLL_STATUS_EXPIRED,
}


def transition_club(current_state: str, event: str, actor_role: str) -> str:
    """Transition club status according to BW-GYM-03."""
    key = (current_state, event, actor_role)
    if key not in CLUB_TRANSITIONS:
        raise DomainStateError(
            f"Cannot transition club from {current_state} on {event} by {actor_role}"
        )
    return CLUB_TRANSITIONS[key]


def transition_membership(current_state: str, event: str, actor_role: str) -> str:
    """Transition membership status according to BW-GYM-01."""
    key = (current_state, event, actor_role)
    if key not in MEMBERSHIP_TRANSITIONS:
        raise DomainStateError(
            f"Cannot transition membership from {current_state} on {event} by {actor_role}"
        )
    return MEMBERSHIP_TRANSITIONS[key]


def transition_poll(current_state: str, event: str, actor_role: str) -> str:
    """Transition poll status according to BW-GYM-02."""
    key = (current_state, event, actor_role)
    if key not in POLL_TRANSITIONS:
        raise DomainStateError(
            f"Cannot transition poll from {current_state} on {event} by {actor_role}"
        )
    return POLL_TRANSITIONS[key]
