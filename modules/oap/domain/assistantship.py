"""CW-OAP-04: PG assistantship claim workflow (pure Python).

OA-BR-42: both supervisor-role verifications are required, in either order,
and one does not replace the other.
OA-BR-52: the two roles stay separate verifications even when one faculty
member holds both.
OA-BR-46: no step may be skipped.
There is no supervisor or Department Administrator reject path, and no
withdrawal.
"""
from modules.oap.domain.errors import InvalidTransition

NO_CLAIM = "No submitted claim"
AWAITING_DUAL = "Awaiting Dual Supervisor Verification"
AWAITING_OTHER = "Awaiting Other Supervisor Verification"
AWAITING_DEPARTMENT = "Awaiting Department Review"
AWAITING_HOD = "Awaiting HoD Decision"
APPROVED = "Approved – Awaiting Stipend Processing"  # noqa: RUF001
REJECTED = "Rejected"
STIPEND_PROCESSED = "Stipend Processed"

START_STATE = NO_CLAIM
INITIAL_STATE = AWAITING_DUAL

STATE_CHOICES = [
    (state, state)
    for state in (
        AWAITING_DUAL,
        AWAITING_OTHER,
        AWAITING_DEPARTMENT,
        AWAITING_HOD,
        APPROVED,
        REJECTED,
        STIPEND_PROCESSED,
    )
]

TERMINAL_STATES = {REJECTED, STIPEND_PROCESSED}

ROLE_THESIS = "thesis_supervisor"
ROLE_TA = "ta_supervisor"
ROLES = (ROLE_THESIS, ROLE_TA)
ROLE_CHOICES = [(r, r) for r in ROLES]

ACTION_PERMISSION = {
    "submit": "oap.assistantship.submit",
    "verify": "oap.assistantship.verify",
    "forward": "oap.assistantship.review",
    "approve": "oap.assistantship.decide",
    "reject": "oap.assistantship.decide",
    "process_stipend": "oap.assistantship.process_stipend",
}

# Rows 4-7 (rows 2-3 depend on which role verified, see verify()).
TRANSITIONS = {
    (AWAITING_DEPARTMENT, "forward"): AWAITING_HOD,  # OA-UC-34
    (AWAITING_HOD, "approve"): APPROVED,  # OA-UC-35
    (AWAITING_HOD, "reject"): REJECTED,  # OA-UC-35
    (APPROVED, "process_stipend"): STIPEND_PROCESSED,  # OA-UC-36
}


def submit(state, thesis_supervisor_resolved, ta_supervisor_resolved):
    """Row 1 (OA-UC-31). Both supervisor roles must resolve (E1)."""
    if state != NO_CLAIM:
        raise InvalidTransition(f"Cannot apply action 'submit' in state '{state}'")
    if not (thesis_supervisor_resolved and ta_supervisor_resolved):
        raise InvalidTransition(
            "Cannot apply action 'submit': both supervisor roles must resolve"
        )
    return AWAITING_DUAL


def verify(state, already_verified_roles, role):
    """Rows 2 and 3 (OA-UC-33)."""
    if role not in ROLES:
        raise ValueError(f"Unknown supervisor role: '{role}'")
    verified = set(already_verified_roles)
    if role in verified:
        raise InvalidTransition(
            f"Cannot apply action 'verify' in state '{state}': "
            f"role '{role}' already verified"
        )
    if state == AWAITING_DUAL and not verified:
        return AWAITING_OTHER
    other = ROLE_TA if role == ROLE_THESIS else ROLE_THESIS
    if state == AWAITING_OTHER and verified == {other}:
        return AWAITING_DEPARTMENT
    raise InvalidTransition(f"Cannot apply action 'verify' in state '{state}'")


def transition(state, action):
    try:
        return TRANSITIONS[(state, action)]
    except KeyError:
        raise InvalidTransition(
            f"Cannot apply action '{action}' in state '{state}'"
        ) from None
