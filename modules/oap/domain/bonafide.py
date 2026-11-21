"""CW-OAP-02: bonafide certificate request workflow (pure Python)."""
from modules.oap.domain.errors import InvalidTransition

NO_REQUEST = "No submitted bonafide request"
SUBMITTED = "Submitted – Awaiting Academic Administrator"  # noqa: RUF001
APPROVED = "Approved – Certificate Available"  # noqa: RUF001
REJECTED = "Rejected"

START_STATE = NO_REQUEST
INITIAL_STATE = SUBMITTED

TRANSITIONS = {
    (NO_REQUEST, "submit"): SUBMITTED,  # Student, OA-UC-11
    (SUBMITTED, "approve"): APPROVED,  # Academic Administrator, OA-UC-12
    (SUBMITTED, "reject"): REJECTED,  # Academic Administrator, OA-UC-12
}

ACTION_PERMISSION = {
    "submit": "oap.bonafide.submit",
    "approve": "oap.bonafide.decide",
    "reject": "oap.bonafide.decide",
}

TERMINAL_STATES = {APPROVED, REJECTED}

STATE_CHOICES = [
    (state, state) for state in (SUBMITTED, APPROVED, REJECTED)
]


def transition(state, action):
    try:
        return TRANSITIONS[(state, action)]
    except KeyError:
        raise InvalidTransition(
            f"Cannot apply action '{action}' in state '{state}'"
        ) from None
