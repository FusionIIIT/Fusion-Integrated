"""Declarative state machine for ELM workflows (CW-EL-01, CW-EL-02, CW-EL-03, CW-EL-04).

Follows the Fusion Module Authoring Guide convention:
- Declarative transitions tuple
- Pure Python (no Django imports)
- Raises InvalidTransition on illegal movements
"""
from dataclasses import dataclass
from typing import Callable

from .entities import LeaveStatus
from .errors import InvalidTransition


@dataclass(frozen=True)
class Transition:
    frm: LeaveStatus
    to: LeaveStatus
    permission: str | None = None
    description: str = ""


TRANSITIONS: tuple[Transition, ...] = (
    # CW-EL-01: Submission -> Recommendations
    Transition(LeaveStatus.SUBMITTED, LeaveStatus.RECOMMENDED, description="Unit head recommends higher-sanction request"),
    Transition(LeaveStatus.SUBMITTED, LeaveStatus.NOT_RECOMMENDED, description="Unit head does not recommend, advances to final authority"),

    # CW-EL-01: Direct decisions (Unit head for CL/RH, Director self-sanction)
    Transition(LeaveStatus.SUBMITTED, LeaveStatus.APPROVED, description="Unit head or Director approves leave"),
    Transition(LeaveStatus.SUBMITTED, LeaveStatus.REJECTED, description="Unit head or Director rejects leave"),

    # CW-EL-01: Final decision following recommendation
    Transition(LeaveStatus.RECOMMENDED, LeaveStatus.APPROVED, description="Sanctioning authority approves recommended leave"),
    Transition(LeaveStatus.RECOMMENDED, LeaveStatus.REJECTED, description="Sanctioning authority rejects recommended leave"),
    Transition(LeaveStatus.NOT_RECOMMENDED, LeaveStatus.APPROVED, description="Sanctioning authority overrides non-recommendation and approves"),
    Transition(LeaveStatus.NOT_RECOMMENDED, LeaveStatus.REJECTED, description="Sanctioning authority rejects non-recommended leave"),

    # CW-EL-01: Immediate withdrawal before final approval (BR-EL-022)
    Transition(LeaveStatus.SUBMITTED, LeaveStatus.WITHDRAWN, description="Applicant withdraws pending submitted leave"),
    Transition(LeaveStatus.RECOMMENDED, LeaveStatus.WITHDRAWN, description="Applicant withdraws pending recommended leave"),
    Transition(LeaveStatus.NOT_RECOMMENDED, LeaveStatus.WITHDRAWN, description="Applicant withdraws pending non-recommended leave"),

    # CW-EL-02: Approved leave cancellation before start date (BR-EL-023)
    Transition(LeaveStatus.APPROVED, LeaveStatus.CANCELLED, description="Approved cancellation marks leave cancelled"),
)

TERMINAL_STATES = {
    LeaveStatus.APPROVED,
    LeaveStatus.REJECTED,
    LeaveStatus.WITHDRAWN,
    LeaveStatus.CANCELLED,
}


def validate_transition(from_status: str, to_status: str) -> None:
    """Validate whether a transition from from_status to to_status is allowed."""
    for t in TRANSITIONS:
        if t.frm.value == from_status and t.to.value == to_status:
            return
    raise InvalidTransition(f"Illegal workflow transition from '{from_status}' to '{to_status}'.")


def validate_step_decision(step_type: str, decision: str) -> None:
    """Validate that a decision matches the kind of approval step."""
    valid_decisions = {
        "recommendation": {"recommended", "not_recommended"},
        "final_decision": {"approved", "rejected"},
        "establishment_verification": {"approved", "rejected"},
    }
    if decision not in valid_decisions.get(step_type, set()):
        raise InvalidTransition(
            f"Decision '{decision}' is not valid for a {step_type} step."
        )
