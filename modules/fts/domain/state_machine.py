"""FTS lifecycle state machine (BW-FTS-01..08, CW-FTS-01..02)."""
from __future__ import annotations

from dataclasses import dataclass

DRAFT = "draft"
CIRCULATING = "circulating"
ARCHIVED = "archived"
DISCARDED = "discarded"

VALID_STATES = frozenset({DRAFT, CIRCULATING, ARCHIVED, DISCARDED})
TERMINAL_STATES = frozenset({ARCHIVED, DISCARDED})

EVENT_SAVE_DRAFT = "save_draft"
EVENT_SUBMIT_CREATE = "submit_create"
EVENT_EDIT_DRAFT = "edit_draft"
EVENT_DISCARD = "discard"
EVENT_FORWARD = "forward"
EVENT_RETURN = "return"
EVENT_ARCHIVE = "archive"


class InvalidFileStateTransitionError(Exception):
    """Raised when an illegal transition is attempted."""

    def __init__(self, from_state: str | None, event: str, message: str) -> None:
        super().__init__(message)
        self.from_state = from_state
        self.event = event


@dataclass(frozen=True)
class TransitionRule:
    from_state: str | None
    event: str
    target_state: str


TRANSITIONS: dict[tuple[str | None, str], str] = {
    (None, EVENT_SAVE_DRAFT): DRAFT,
    (None, EVENT_SUBMIT_CREATE): CIRCULATING,
    (DRAFT, EVENT_EDIT_DRAFT): DRAFT,
    (DRAFT, EVENT_DISCARD): DISCARDED,
    (DRAFT, EVENT_FORWARD): CIRCULATING,
    (CIRCULATING, EVENT_FORWARD): CIRCULATING,
    (CIRCULATING, EVENT_RETURN): CIRCULATING,
    (CIRCULATING, EVENT_ARCHIVE): ARCHIVED,
}


def can_transition(from_state: str | None, event: str) -> bool:
    """Check whether a transition from from_state on event is permitted."""
    if from_state in TERMINAL_STATES:
        return False
    return (from_state, event) in TRANSITIONS


def transition(from_state: str | None, event: str) -> str:
    """Advance to next state or raise InvalidFileStateTransitionError."""
    if from_state in TERMINAL_STATES:
        raise InvalidFileStateTransitionError(
            from_state,
            event,
            f"Cannot perform '{event}' on terminal file state '{from_state}'.",
        )
    target = TRANSITIONS.get((from_state, event))
    if not target:
        raise InvalidFileStateTransitionError(
            from_state,
            event,
            f"Transition from state '{from_state}' on event '{event}' is illegal.",
        )
    return target
