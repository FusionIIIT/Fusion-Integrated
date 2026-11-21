"""CW-OAP-01: leave application workflow (pure Python)."""
from modules.oap.domain.errors import InvalidTransition

NO_APPLICATION = "No submitted leave application"
SUBMITTED = "Submitted – Awaiting HoD Decision"  # noqa: RUF001
APPROVED = "Approved"
REJECTED = "Rejected"

START_STATE = NO_APPLICATION
INITIAL_STATE = SUBMITTED

TRANSITIONS = {
    (NO_APPLICATION, "submit"): SUBMITTED,  # Student, OA-UC-01
    (SUBMITTED, "approve"): APPROVED,  # HoD, OA-UC-03
    (SUBMITTED, "reject"): REJECTED,  # HoD, OA-UC-03
}

ACTION_PERMISSION = {
    "submit": "oap.leave.submit",
    "approve": "oap.leave.decide",
    "reject": "oap.leave.decide",
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
