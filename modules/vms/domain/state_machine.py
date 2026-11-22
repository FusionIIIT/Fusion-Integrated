"""Pure python state machine and transition rules for VMS.

ZERO framework imports allowed here.
"""

from __future__ import annotations

from typing import Final, Literal

VisitStatus = Literal[
    "PENDING_APPROVAL",
    "APPROVED",
    "REJECTED",
    "EXPIRED",
    "CANCELLED",
    "CHECKED_IN",
    "CHECKED_OUT",
    "AUTO_CHECKED_OUT",
    "TERMINATED_EARLY",
]

ALLOWED_TRANSITIONS: Final[dict[str, set[str]]] = {
    "PENDING_APPROVAL": {"APPROVED", "REJECTED", "EXPIRED", "CANCELLED"},
    "APPROVED": {"CHECKED_IN", "TERMINATED_EARLY", "CANCELLED"},
    "CHECKED_IN": {"CHECKED_OUT", "AUTO_CHECKED_OUT", "TERMINATED_EARLY"},
    "REJECTED": set(),
    "EXPIRED": set(),
    "CANCELLED": set(),
    "CHECKED_OUT": set(),
    "AUTO_CHECKED_OUT": set(),
    "TERMINATED_EARLY": set(),
}

TERMINAL_STATES: Final[set[str]] = {
    "REJECTED",
    "EXPIRED",
    "CANCELLED",
    "CHECKED_OUT",
    "AUTO_CHECKED_OUT",
    "TERMINATED_EARLY",
}


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal state transition is attempted."""


class MissingJustificationError(ValueError):
    """Raised when an action requires an explicit audit justification/reason."""


class UnauthorizedActionError(PermissionError):
    """Raised when an actor attempts an action outside their role scope."""


def can_transition(from_state: str, to_state: str) -> bool:
    """Return True if transition from `from_state` to `to_state` is valid."""
    allowed = ALLOWED_TRANSITIONS.get(from_state, set())
    return to_state in allowed


def assert_can_transition(from_state: str, to_state: str) -> None:
    """Assert transition is valid, else raise InvalidStateTransitionError."""
    if not can_transition(from_state, to_state):
        raise InvalidStateTransitionError(
            f"Cannot transition visit from '{from_state}' to '{to_state}'."
        )


def validate_rejection(reason: str | None) -> None:
    """Rejection requires an explicit reason."""
    if not reason or not reason.strip():
        raise MissingJustificationError("A rejection reason is required.")


def validate_termination(reason: str | None) -> None:
    """Early termination requires a justification."""
    if not reason or not reason.strip():
        raise MissingJustificationError("An early termination reason is required.")


def validate_manual_override(reason: str | None) -> None:
    """Manual gate override requires a mandatory justification."""
    if not reason or not reason.strip():
        raise MissingJustificationError("A manual override reason is required.")
