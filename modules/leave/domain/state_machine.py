"""Declarative state machine for leave workflows (WF-EL-01..05)."""
from __future__ import annotations

from core.api.exceptions import ConflictError

DRAFT = "draft"
SUBMITUTE_PENDING = "substitute_pending"
UNDER_REVIEW = "under_review"
APPROVED = "approved"
REJECTED = "rejected"
WITHDRAWN = "withdrawn"
CANCEL_REQUESTED = "cancel_requested"
CANCELLED = "cancelled"
EXTENSION_REQUESTED = "extension_requested"
RESUMPTION_SUBMITTED = "resumption_submitted"
CLOSED = "closed"

TERMINAL_STATES = {REJECTED, WITHDRAWN, CANCELLED, CLOSED}

ALLOWED_TRANSITIONS = {
    DRAFT: {SUBMITUTE_PENDING, UNDER_REVIEW, WITHDRAWN},
    SUBMITUTE_PENDING: {UNDER_REVIEW, WITHDRAWN},
    UNDER_REVIEW: {APPROVED, REJECTED, WITHDRAWN},
    APPROVED: {CANCEL_REQUESTED, EXTENSION_REQUESTED, RESUMPTION_SUBMITTED},
    CANCEL_REQUESTED: {CANCELLED, APPROVED},
    EXTENSION_REQUESTED: {APPROVED, REJECTED, WITHDRAWN},
    RESUMPTION_SUBMITTED: {CLOSED},
}


def validate_transition(current_state: str, next_state: str) -> None:
    """Ensure the state transition is valid per business rules."""
    allowed = ALLOWED_TRANSITIONS.get(current_state, set())
    if next_state not in allowed:
        raise ConflictError(
            f"Cannot transition leave application from {current_state!r} to {next_state!r}.",
            code="invalid_state_transition",
        )
