DRAFT = "draft"
SUBSTITUTE_PENDING = "substitute_pending"
SUBSTITUTE_DECLINED = "substitute_declined"
UNDER_REVIEW = "under_review"
ESTABLISHMENT_REVIEW = "establishment_review"
SANCTION_REVIEW = "sanction_review"
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
    DRAFT: {SUBSTITUTE_PENDING, UNDER_REVIEW, WITHDRAWN},
    SUBSTITUTE_PENDING: {UNDER_REVIEW, SUBSTITUTE_DECLINED, WITHDRAWN, APPROVED},
    SUBSTITUTE_DECLINED: {SUBSTITUTE_PENDING, WITHDRAWN},
    UNDER_REVIEW: {APPROVED, REJECTED, ESTABLISHMENT_REVIEW, SANCTION_REVIEW, WITHDRAWN},
    ESTABLISHMENT_REVIEW: {SANCTION_REVIEW, WITHDRAWN},
    SANCTION_REVIEW: {APPROVED, REJECTED, WITHDRAWN},
    APPROVED: {CANCEL_REQUESTED, EXTENSION_REQUESTED, RESUMPTION_SUBMITTED},
    CANCEL_REQUESTED: {CANCELLED, APPROVED},
    EXTENSION_REQUESTED: {APPROVED, REJECTED, WITHDRAWN},
    RESUMPTION_SUBMITTED: {CLOSED},
}

def validate_transition(current_state: str, next_state: str) -> bool:
    curr = str(current_state).lower()
    nxt = str(next_state).lower()
    allowed = ALLOWED_TRANSITIONS.get(curr, set())
    if nxt not in allowed:
        raise ValueError(f"Invalid transition from {current_state} to {next_state}")
    return True

def is_terminal_state(state: str) -> bool:
    return str(state).lower() in TERMINAL_STATES