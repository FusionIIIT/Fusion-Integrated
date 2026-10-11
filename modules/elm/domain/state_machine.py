from typing import FrozenSet, Tuple
from enum import StrEnum
from dataclasses import dataclass

class InvalidTransition(Exception):
    """Raised when an invalid transition is attempted."""

class PermissionDenied(PermissionError):
    """Raised when a transition exists but permission is missing."""

class Status(StrEnum):
    DRAFT = "DRAFT"
    PENDING_UNIT_HEAD = "PENDING_UNIT_HEAD"
    PENDING_ESTABLISHMENT = "PENDING_ESTABLISHMENT"
    PENDING_FINAL_SANCTION = "PENDING_FINAL_SANCTION"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"
    CANCELLED = "CANCELLED"

@dataclass(frozen=True)
class Transition:
    """Defines a transition from one status to another."""
    from_status: Status
    to_status: Status
    permission: str

TRANSITIONS: Tuple[Transition, ...] = (
    Transition(Status.DRAFT, Status.PENDING_UNIT_HEAD, "elm.leave_request.create"),
    Transition(Status.PENDING_UNIT_HEAD, Status.APPROVED, "elm.leave_request.approve"),
    Transition(Status.PENDING_UNIT_HEAD, Status.REJECTED, "elm.leave_request.approve"),
    Transition(Status.PENDING_UNIT_HEAD, Status.PENDING_ESTABLISHMENT, "elm.leave_request.approve"),
    Transition(Status.PENDING_ESTABLISHMENT, Status.PENDING_FINAL_SANCTION, "elm.leave_request.approve"),
    Transition(Status.PENDING_ESTABLISHMENT, Status.REJECTED, "elm.leave_request.approve"),
    Transition(Status.PENDING_FINAL_SANCTION, Status.APPROVED, "elm.leave_request.approve"),
    Transition(Status.PENDING_FINAL_SANCTION, Status.REJECTED, "elm.leave_request.approve"),
    Transition(Status.PENDING_UNIT_HEAD, Status.WITHDRAWN, "elm.leave_request.update"),
    Transition(Status.PENDING_ESTABLISHMENT, Status.WITHDRAWN, "elm.leave_request.update"),
    Transition(Status.PENDING_FINAL_SANCTION, Status.WITHDRAWN, "elm.leave_request.update"),
    Transition(Status.APPROVED, Status.CANCELLED, "elm.leave_request.update"),
)

def validate_transition(from_status: Status, to_status: Status, permissions: FrozenSet[str]) -> None:
    """Validate a transition from one status to another with a given permission."""
    for transition in TRANSITIONS:
        if transition.from_status == from_status and transition.to_status == to_status:
            if "*" in permissions or transition.permission in permissions:
                return
    if not any(transition.from_status == from_status and transition.to_status == to_status for transition in TRANSITIONS):
        raise InvalidTransition(f"No transition from {from_status} to {to_status}")
    raise PermissionDenied(f"No permission to transition from {from_status} to {to_status}")
