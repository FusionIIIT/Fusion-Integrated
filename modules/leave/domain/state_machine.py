"""Declarative state machine for leave workflows (WF-EL-01..05)."""

from __future__ import annotations

from modules.leave.domain.exceptions import InvalidStateTransitionError

DRAFT = "draft"
SUBSTITUTE_PENDING = "substitute_pending"
APPLICANT_ACTION_REQUIRED = "applicant_action_required"
UNDER_REVIEW = "under_review"
APPROVED = "approved"
REJECTED = "rejected"
WITHDRAWN = "withdrawn"
CANCEL_REQUESTED = "cancel_requested"
CANCELLED = "cancelled"
EXTENSION_REQUESTED = "extension_requested"
RESUMPTION_SUBMITTED = "resumption_submitted"
CLOSED = "closed"
RESUMPTION_REVIEWED_NORMAL = "resumption_reviewed_normal"
RESUMPTION_REVIEWED_EARLY = "resumption_reviewed_early"
RESUMPTION_REVIEWED_LATE = "resumption_reviewed_late"

TERMINAL_STATES = {
    REJECTED,
    WITHDRAWN,
    CANCELLED,
    CLOSED,
    RESUMPTION_REVIEWED_NORMAL,
    RESUMPTION_REVIEWED_EARLY,
    RESUMPTION_REVIEWED_LATE,
}

ALLOWED_TRANSITIONS = {
    DRAFT: {SUBSTITUTE_PENDING, UNDER_REVIEW, WITHDRAWN},
    SUBSTITUTE_PENDING: {UNDER_REVIEW, APPLICANT_ACTION_REQUIRED, WITHDRAWN},
    APPLICANT_ACTION_REQUIRED: {SUBSTITUTE_PENDING, WITHDRAWN},
    UNDER_REVIEW: {APPROVED, REJECTED, WITHDRAWN},
    APPROVED: {CANCEL_REQUESTED, EXTENSION_REQUESTED, RESUMPTION_SUBMITTED},
    CANCEL_REQUESTED: {CANCELLED, APPROVED},
    EXTENSION_REQUESTED: {APPROVED, REJECTED, WITHDRAWN},
    RESUMPTION_SUBMITTED: {
        RESUMPTION_REVIEWED_NORMAL,
        RESUMPTION_REVIEWED_EARLY,
        RESUMPTION_REVIEWED_LATE,
    },
}


def validate_transition(current_state: str, next_state: str) -> None:
    """Ensure the state transition is valid per business rules."""
    allowed = ALLOWED_TRANSITIONS.get(current_state, set())
    if next_state not in allowed:
        raise InvalidStateTransitionError(current_state, next_state)
