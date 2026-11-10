"""BW-OAP-09: PG seminar request workflow (pure Python)."""
from modules.oap.domain.errors import InvalidTransition

NO_REQUEST = "No submitted seminar request"
AWAITING_SCHEDULING = "Awaiting Scheduling"
SCHEDULED = "Scheduled"

START_STATE = NO_REQUEST
INITIAL_STATE = AWAITING_SCHEDULING

TRANSITIONS = {
    (NO_REQUEST, "submit"): AWAITING_SCHEDULING,  # PG Student, OA-UC-51
    (AWAITING_SCHEDULING, "schedule"): SCHEDULED,  # Department Administrator, OA-UC-53
}

ACTION_PERMISSION = {
    "submit": "oap.seminar.request",
    "schedule": "oap.seminar.schedule",
}

TERMINAL_STATES = {SCHEDULED}

STATE_CHOICES = [
    (state, state) for state in (AWAITING_SCHEDULING, SCHEDULED)
]


def transition(state, action):
    try:
        return TRANSITIONS[(state, action)]
    except KeyError:
        raise InvalidTransition(
            f"Cannot apply action '{action}' in state '{state}'"
        ) from None
