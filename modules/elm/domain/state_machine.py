"""ELM domain state machine.

Defines the authoritative lifecycle states and valid transitions for leave
requests based on the Fusion ERP ELM specifications (CW-EL-01, CW-EL-02,
BR-EL-014 through BR-EL-023).
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import FrozenSet, Tuple


class InvalidTransition(Exception):
    """Raised when an invalid transition is attempted."""


class PermissionDenied(PermissionError):
    """Raised when a transition exists but permission is missing."""


class Status(StrEnum):
    # Initial / Preparation
    DRAFT = "DRAFT"

    # Substitute Consent Gate (CW-EL-01, BR-EL-014, BR-EL-015)
    AWAITING_SUBSTITUTE_RESPONSE = "AWAITING_SUBSTITUTE_RESPONSE"
    APPLICANT_ACTION_REQUIRED = "APPLICANT_ACTION_REQUIRED"

    # Main Approval Pipeline (CW-EL-01, BR-EL-016 - BR-EL-020)
    PENDING_UNIT_HEAD = "PENDING_UNIT_HEAD"
    PENDING_ESTABLISHMENT = "PENDING_ESTABLISHMENT"
    PENDING_FINAL_SANCTION = "PENDING_FINAL_SANCTION"
    AWAITING_DIRECTOR_SELF_SANCTION = "AWAITING_DIRECTOR_SELF_SANCTION"

    # Cancellation Pipeline for Approved Leave (CW-EL-02, BR-EL-023)
    CANCELLATION_PENDING_UNIT_HEAD = "CANCELLATION_PENDING_UNIT_HEAD"
    CANCELLATION_PENDING_ESTABLISHMENT = "CANCELLATION_PENDING_ESTABLISHMENT"
    CANCELLATION_PENDING_FINAL_DECISION = "CANCELLATION_PENDING_FINAL_DECISION"

    # Terminal Outcomes
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


# Authoritative state transitions covering CW-EL-01 and CW-EL-02:
TRANSITIONS: Tuple[Transition, ...] = (
    # --- CW-EL-01: Submission & Substitute Consent Gate ---
    # Apply with no substitute required (standard employee)
    Transition(Status.DRAFT, Status.PENDING_UNIT_HEAD, "elm.leave_request.create"),
    # Apply with substitute required
    Transition(Status.DRAFT, Status.AWAITING_SUBSTITUTE_RESPONSE, "elm.leave_request.create"),
    # Apply with no substitute required (Director self-sanction route)
    Transition(Status.DRAFT, Status.AWAITING_DIRECTOR_SELF_SANCTION, "elm.leave_request.create"),

    # Substitute accepts -> routes to Unit Head (standard) or Director
    Transition(Status.AWAITING_SUBSTITUTE_RESPONSE, Status.PENDING_UNIT_HEAD, "elm.leave_request.update"),
    Transition(Status.AWAITING_SUBSTITUTE_RESPONSE, Status.AWAITING_DIRECTOR_SELF_SANCTION, "elm.leave_request.update"),

    # Substitute declines -> applicant action required (nominate replacement or withdraw)
    Transition(Status.AWAITING_SUBSTITUTE_RESPONSE, Status.APPLICANT_ACTION_REQUIRED, "elm.leave_request.update"),

    # Replacement nominated -> back to awaiting substitute response
    Transition(Status.APPLICANT_ACTION_REQUIRED, Status.AWAITING_SUBSTITUTE_RESPONSE, "elm.leave_request.update"),

    # --- CW-EL-01: Unit Head Review ---
    # Final approve/reject for CL/RH
    Transition(Status.PENDING_UNIT_HEAD, Status.APPROVED, "elm.leave_request.approve"),
    Transition(Status.PENDING_UNIT_HEAD, Status.REJECTED, "elm.leave_request.approve"),
    # Recommendation recorded for higher-sanction leave
    Transition(Status.PENDING_UNIT_HEAD, Status.PENDING_ESTABLISHMENT, "elm.leave_request.approve"),
    Transition(Status.PENDING_UNIT_HEAD, Status.PENDING_FINAL_SANCTION, "elm.leave_request.approve"),

    # --- CW-EL-01: Establishment Routing ---
    Transition(Status.PENDING_ESTABLISHMENT, Status.PENDING_FINAL_SANCTION, "elm.leave_request.approve"),
    Transition(Status.PENDING_ESTABLISHMENT, Status.REJECTED, "elm.leave_request.approve"),

    # --- CW-EL-01: Final Sanction Decision ---
    Transition(Status.PENDING_FINAL_SANCTION, Status.APPROVED, "elm.leave_request.approve"),
    Transition(Status.PENDING_FINAL_SANCTION, Status.REJECTED, "elm.leave_request.approve"),

    # --- CW-EL-01: Director Self-Sanction ---
    Transition(Status.AWAITING_DIRECTOR_SELF_SANCTION, Status.APPROVED, "elm.leave_request.approve"),
    Transition(Status.AWAITING_DIRECTOR_SELF_SANCTION, Status.REJECTED, "elm.leave_request.approve"),

    # --- CW-EL-01: Cross-cutting immediate withdrawal from any pending pre-final state (BR-EL-022) ---
    Transition(Status.AWAITING_SUBSTITUTE_RESPONSE, Status.WITHDRAWN, "elm.leave_request.update"),
    Transition(Status.APPLICANT_ACTION_REQUIRED, Status.WITHDRAWN, "elm.leave_request.update"),
    Transition(Status.PENDING_UNIT_HEAD, Status.WITHDRAWN, "elm.leave_request.update"),
    Transition(Status.PENDING_ESTABLISHMENT, Status.WITHDRAWN, "elm.leave_request.update"),
    Transition(Status.PENDING_FINAL_SANCTION, Status.WITHDRAWN, "elm.leave_request.update"),
    Transition(Status.AWAITING_DIRECTOR_SELF_SANCTION, Status.WITHDRAWN, "elm.leave_request.update"),

    # --- CW-EL-02: Approved Leave Cancellation before start (BR-EL-023) ---
    Transition(Status.APPROVED, Status.CANCELLATION_PENDING_UNIT_HEAD, "elm.leave_request.update"),

    # Unit Head decides on cancellation (CL/RH) or routes higher-sanction
    Transition(Status.CANCELLATION_PENDING_UNIT_HEAD, Status.CANCELLED, "elm.leave_request.approve"),
    Transition(Status.CANCELLATION_PENDING_UNIT_HEAD, Status.APPROVED, "elm.leave_request.approve"),  # Rejected cancellation preserves approval
    Transition(Status.CANCELLATION_PENDING_UNIT_HEAD, Status.CANCELLATION_PENDING_ESTABLISHMENT, "elm.leave_request.approve"),
    Transition(Status.CANCELLATION_PENDING_UNIT_HEAD, Status.CANCELLATION_PENDING_FINAL_DECISION, "elm.leave_request.approve"),

    # Establishment routes cancellation
    Transition(Status.CANCELLATION_PENDING_ESTABLISHMENT, Status.CANCELLATION_PENDING_FINAL_DECISION, "elm.leave_request.approve"),

    # Final Sanctioning Authority decides on cancellation
    Transition(Status.CANCELLATION_PENDING_FINAL_DECISION, Status.CANCELLED, "elm.leave_request.approve"),
    Transition(Status.CANCELLATION_PENDING_FINAL_DECISION, Status.APPROVED, "elm.leave_request.approve"),  # Rejected cancellation preserves approval
)


def validate_transition(from_status: Status, to_status: Status, permissions: FrozenSet[str]) -> None:
    """Validate a transition from one status to another with a given permission set."""
    for transition in TRANSITIONS:
        if transition.from_status == from_status and transition.to_status == to_status:
            if "*" in permissions or transition.permission in permissions:
                return
    if not any(transition.from_status == from_status and transition.to_status == to_status for transition in TRANSITIONS):
        raise InvalidTransition(f"No transition from {from_status} to {to_status}")
    raise PermissionDenied(f"No permission to transition from {from_status} to {to_status}")
