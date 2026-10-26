# Declarative state machine for leave application lifecycle (BR-EL-022, BR-EL-023, BR-EL-034)
from dataclasses import dataclass

from core.api.exceptions import ConflictError
from modules.leave.domain.constants import (
    STATUS_APPROVED,
    STATUS_CANCELLED,
    STATUS_PENDING,
    STATUS_REJECTED,
    STATUS_WITHDRAWN,
    TERMINAL_STATUSES,
)

ACTOR_APPLICANT = "applicant"
ACTOR_APPROVER = "approver"
ACTOR_SYSTEM = "system"


@dataclass(frozen=True)
class LeaveTransition:
    frm: str
    to: str
    actors: frozenset[str]
    description: str


LEAVE_TRANSITIONS: tuple[LeaveTransition, ...] = (
    LeaveTransition(
        frm=STATUS_PENDING,
        to=STATUS_APPROVED,
        actors=frozenset({ACTOR_APPROVER}),
        description="Approver sanctions pending leave application",
    ),
    LeaveTransition(
        frm=STATUS_PENDING,
        to=STATUS_REJECTED,
        actors=frozenset({ACTOR_APPROVER}),
        description="Approver rejects pending leave application",
    ),
    LeaveTransition(
        frm=STATUS_PENDING,
        to=STATUS_WITHDRAWN,
        actors=frozenset({ACTOR_APPLICANT}),
        description="Applicant withdraws pending application before final approval (BR-EL-022)",
    ),
    LeaveTransition(
        frm=STATUS_APPROVED,
        to=STATUS_CANCELLED,
        actors=frozenset({ACTOR_APPLICANT, ACTOR_APPROVER}),
        description="Cancellation of approved leave prior to start date (BR-EL-023)",
    ),
)

_TRANSITION_INDEX = {(t.frm, t.to): t for t in LEAVE_TRANSITIONS}


def validate_transition(
    current_status: str,
    target_status: str,
    actor_kind: str,
) -> LeaveTransition:
    """Validate that moving from current_status to target_status is permitted for actor_kind."""
    if current_status in TERMINAL_STATUSES:
        raise ConflictError(
            f"Application is in terminal state '{current_status}' and cannot be altered."
        )

    transition = _TRANSITION_INDEX.get((current_status, target_status))
    if transition is None:
        raise ConflictError(
            f"Illegal status transition from '{current_status}' to '{target_status}'."
        )

    if actor_kind not in transition.actors:
        raise ConflictError(
            f"Actor '{actor_kind}' cannot move leave from '{current_status}' to '{target_status}'."
        )

    return transition
