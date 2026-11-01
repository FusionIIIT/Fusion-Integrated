"""Authoritative PMS Lifecycle State Machine (BW-PMS-01 through BW-PMS-16)."""

from __future__ import annotations

from dataclasses import dataclass

from modules.pms.domain.constants import (
    ACTOR_APPLICANT,
    ACTOR_ATTORNEY,
    ACTOR_DIRECTOR,
    ACTOR_PCC_ADMIN,
    ACTOR_SYSTEM,
    STATUS_APPEAL_SUBMITTED,
    STATUS_APPLICANT_APPROVED,
    STATUS_APPROVED,
    STATUS_ASSIGNMENT_OFFERED,
    STATUS_ATTORNEY_ASSIGNED,
    STATUS_AWAITING_APPLICANT_APPROVAL,
    STATUS_BUDGET_APPROVED,
    STATUS_BUDGET_ESCALATED,
    STATUS_BUDGET_REJECTED,
    STATUS_DECISION_MODIFIED,
    STATUS_DO_NOT_RENEW,
    STATUS_DRAFT,
    STATUS_EXPIRED,
    STATUS_FILED,
    STATUS_GRANTED,
    STATUS_NEEDS_REVISION,
    STATUS_OFFICE_ACTION_RECORDED,
    STATUS_REJECTED,
    STATUS_REJECTION_UPHELD,
    STATUS_REMANDED_FOR_AMENDMENT,
    STATUS_RENEWAL_APPROVED,
    STATUS_RENEWAL_DECISION_REQUESTED,
    STATUS_RENEWED,
    STATUS_RESPONSE_READY,
    STATUS_RESPONSE_SUBMITTED,
    STATUS_RESUBMITTED,
    STATUS_SUBMITTED,
    STATUS_UNDER_REVIEW,
    STATUS_WITHDRAWN,
    WITHDRAWAL_ELIGIBLE_STATUSES,
)
from modules.pms.domain.exceptions import (
    ActorNotAllowedError,
    InvalidTransitionError,
)


@dataclass(frozen=True)
class TransitionEdge:
    from_status: str
    to_status: str
    allowed_actors: frozenset[str]
    workflow_id: str


# Transition graph directly encoding the 16 Basis Workflows
TRANSITIONS: tuple[TransitionEdge, ...] = (
    # BW-PMS-01: Initial Review Approval Path
    TransitionEdge(STATUS_DRAFT, STATUS_SUBMITTED, frozenset({ACTOR_APPLICANT}), "BW-PMS-01"),
    TransitionEdge(
        STATUS_SUBMITTED,
        STATUS_UNDER_REVIEW,
        frozenset({ACTOR_PCC_ADMIN, ACTOR_SYSTEM}),
        "BW-PMS-01",
    ),
    TransitionEdge(
        STATUS_UNDER_REVIEW,
        STATUS_APPROVED,
        frozenset({ACTOR_DIRECTOR}),
        "BW-PMS-01",
    ),
    # BW-PMS-02: Revision and Re-Approval Path
    TransitionEdge(
        STATUS_UNDER_REVIEW,
        STATUS_NEEDS_REVISION,
        frozenset({ACTOR_DIRECTOR}),
        "BW-PMS-02",
    ),
    TransitionEdge(
        STATUS_NEEDS_REVISION,
        STATUS_RESUBMITTED,
        frozenset({ACTOR_APPLICANT}),
        "BW-PMS-02",
    ),
    TransitionEdge(
        STATUS_RESUBMITTED,
        STATUS_UNDER_REVIEW,
        frozenset({ACTOR_PCC_ADMIN, ACTOR_SYSTEM}),
        "BW-PMS-02",
    ),
    TransitionEdge(STATUS_NEEDS_REVISION, STATUS_EXPIRED, frozenset({ACTOR_SYSTEM}), "BW-PMS-02"),
    # BW-PMS-03, 04, 05: Rejection and Appeals
    TransitionEdge(
        STATUS_UNDER_REVIEW,
        STATUS_REJECTED,
        frozenset({ACTOR_DIRECTOR}),
        "BW-PMS-03",
    ),
    TransitionEdge(
        STATUS_REJECTED,
        STATUS_APPEAL_SUBMITTED,
        frozenset({ACTOR_APPLICANT}),
        "BW-PMS-03",
    ),
    TransitionEdge(
        STATUS_APPEAL_SUBMITTED,
        STATUS_REMANDED_FOR_AMENDMENT,
        frozenset({ACTOR_DIRECTOR}),
        "BW-PMS-03",
    ),
    TransitionEdge(
        STATUS_APPEAL_SUBMITTED,
        STATUS_REJECTION_UPHELD,
        frozenset({ACTOR_DIRECTOR}),
        "BW-PMS-04",
    ),
    TransitionEdge(
        STATUS_APPEAL_SUBMITTED,
        STATUS_DECISION_MODIFIED,
        frozenset({ACTOR_DIRECTOR}),
        "BW-PMS-05",
    ),
    TransitionEdge(
        STATUS_REMANDED_FOR_AMENDMENT,
        STATUS_UNDER_REVIEW,
        frozenset({ACTOR_PCC_ADMIN}),
        "BW-PMS-03",
    ),
    TransitionEdge(
        STATUS_DECISION_MODIFIED,
        STATUS_APPROVED,
        frozenset({ACTOR_DIRECTOR}),
        "BW-PMS-05",
    ),
    # BW-PMS-06, 07: Attorney Assignment
    TransitionEdge(
        STATUS_APPROVED,
        STATUS_ASSIGNMENT_OFFERED,
        frozenset({ACTOR_PCC_ADMIN}),
        "BW-PMS-06",
    ),
    TransitionEdge(
        STATUS_BUDGET_APPROVED,
        STATUS_ASSIGNMENT_OFFERED,
        frozenset({ACTOR_PCC_ADMIN}),
        "BW-PMS-06",
    ),
    TransitionEdge(
        STATUS_ASSIGNMENT_OFFERED,
        STATUS_ATTORNEY_ASSIGNED,
        frozenset({ACTOR_ATTORNEY}),
        "BW-PMS-06",
    ),
    TransitionEdge(
        STATUS_ASSIGNMENT_OFFERED,
        STATUS_APPROVED,
        frozenset({ACTOR_ATTORNEY}),
        "BW-PMS-07",
    ),
    TransitionEdge(
        STATUS_ASSIGNMENT_OFFERED,
        STATUS_BUDGET_APPROVED,
        frozenset({ACTOR_ATTORNEY}),
        "BW-PMS-07",
    ),
    # BW-PMS-08, 09, 10: Budget Review
    TransitionEdge(
        STATUS_APPROVED,
        STATUS_BUDGET_APPROVED,
        frozenset({ACTOR_DIRECTOR}),
        "BW-PMS-08",
    ),
    TransitionEdge(
        STATUS_ATTORNEY_ASSIGNED,
        STATUS_BUDGET_APPROVED,
        frozenset({ACTOR_DIRECTOR}),
        "BW-PMS-08",
    ),
    TransitionEdge(
        STATUS_APPROVED,
        STATUS_BUDGET_REJECTED,
        frozenset({ACTOR_DIRECTOR}),
        "BW-PMS-09",
    ),
    TransitionEdge(
        STATUS_ATTORNEY_ASSIGNED,
        STATUS_BUDGET_REJECTED,
        frozenset({ACTOR_DIRECTOR}),
        "BW-PMS-09",
    ),
    TransitionEdge(
        STATUS_APPROVED,
        STATUS_BUDGET_ESCALATED,
        frozenset({ACTOR_DIRECTOR}),
        "BW-PMS-10",
    ),
    TransitionEdge(
        STATUS_ATTORNEY_ASSIGNED,
        STATUS_BUDGET_ESCALATED,
        frozenset({ACTOR_DIRECTOR}),
        "BW-PMS-10",
    ),
    TransitionEdge(
        STATUS_BUDGET_ESCALATED,
        STATUS_BUDGET_APPROVED,
        frozenset({ACTOR_PCC_ADMIN, ACTOR_DIRECTOR}),
        "BW-PMS-10",
    ),
    # BW-PMS-11: External Filing Path
    TransitionEdge(STATUS_APPROVED, STATUS_FILED, frozenset({ACTOR_ATTORNEY}), "BW-PMS-11"),
    TransitionEdge(
        STATUS_ATTORNEY_ASSIGNED,
        STATUS_FILED,
        frozenset({ACTOR_ATTORNEY}),
        "BW-PMS-11",
    ),
    TransitionEdge(
        STATUS_BUDGET_APPROVED,
        STATUS_FILED,
        frozenset({ACTOR_ATTORNEY}),
        "BW-PMS-11",
    ),
    # BW-PMS-12, 13: Office Action Handling
    TransitionEdge(
        STATUS_FILED,
        STATUS_OFFICE_ACTION_RECORDED,
        frozenset({ACTOR_ATTORNEY}),
        "BW-PMS-12",
    ),
    TransitionEdge(
        STATUS_OFFICE_ACTION_RECORDED,
        STATUS_AWAITING_APPLICANT_APPROVAL,
        frozenset({ACTOR_ATTORNEY}),
        "BW-PMS-12",
    ),
    TransitionEdge(
        STATUS_AWAITING_APPLICANT_APPROVAL,
        STATUS_APPLICANT_APPROVED,
        frozenset({ACTOR_APPLICANT}),
        "BW-PMS-12",
    ),
    TransitionEdge(
        STATUS_APPLICANT_APPROVED,
        STATUS_RESPONSE_SUBMITTED,
        frozenset({ACTOR_ATTORNEY}),
        "BW-PMS-12",
    ),
    TransitionEdge(
        STATUS_OFFICE_ACTION_RECORDED,
        STATUS_RESPONSE_READY,
        frozenset({ACTOR_ATTORNEY}),
        "BW-PMS-13",
    ),
    TransitionEdge(
        STATUS_RESPONSE_READY,
        STATUS_RESPONSE_SUBMITTED,
        frozenset({ACTOR_ATTORNEY}),
        "BW-PMS-13",
    ),
    TransitionEdge(
        STATUS_RESPONSE_SUBMITTED,
        STATUS_FILED,
        frozenset({ACTOR_ATTORNEY}),
        "BW-PMS-12",
    ),
    TransitionEdge(
        STATUS_RESPONSE_SUBMITTED,
        STATUS_GRANTED,
        frozenset({ACTOR_ATTORNEY}),
        "BW-PMS-12",
    ),
    TransitionEdge(STATUS_FILED, STATUS_GRANTED, frozenset({ACTOR_ATTORNEY}), "BW-PMS-11"),
    # BW-PMS-14, 15: Post-Grant Maintenance Cycle
    TransitionEdge(
        STATUS_GRANTED,
        STATUS_RENEWAL_DECISION_REQUESTED,
        frozenset({ACTOR_ATTORNEY}),
        "BW-PMS-14",
    ),
    TransitionEdge(
        STATUS_RENEWAL_DECISION_REQUESTED,
        STATUS_RENEWAL_APPROVED,
        frozenset({ACTOR_DIRECTOR}),
        "BW-PMS-14",
    ),
    TransitionEdge(
        STATUS_RENEWAL_APPROVED,
        STATUS_RENEWED,
        frozenset({ACTOR_ATTORNEY}),
        "BW-PMS-14",
    ),
    TransitionEdge(STATUS_RENEWED, STATUS_GRANTED, frozenset({ACTOR_ATTORNEY}), "BW-PMS-14"),
    TransitionEdge(
        STATUS_RENEWAL_DECISION_REQUESTED,
        STATUS_DO_NOT_RENEW,
        frozenset({ACTOR_DIRECTOR}),
        "BW-PMS-15",
    ),
)


def validate_transition(current_status: str, target_status: str, actor: str) -> TransitionEdge:
    """Validate a lifecycle transition against the transition table (BW-PMS-01..16)."""
    # Special check: BW-PMS-16 Pre-filing withdrawal
    if target_status == STATUS_WITHDRAWN:
        if current_status not in WITHDRAWAL_ELIGIBLE_STATUSES:
            raise InvalidTransitionError(
                current_status,
                target_status,
                f"Cannot withdraw in status {current_status!r}. Permitted before filing.",
            )
        if actor not in (ACTOR_APPLICANT, ACTOR_PCC_ADMIN):
            raise ActorNotAllowedError(actor, f"withdraw application in status {current_status!r}")
        return TransitionEdge(current_status, target_status, frozenset({actor}), "BW-PMS-16")

    # Match in transitions table
    matches = [
        e for e in TRANSITIONS if e.from_status == current_status and e.to_status == target_status
    ]
    if not matches:
        raise InvalidTransitionError(current_status, target_status)

    edge = matches[0]
    if actor not in edge.allowed_actors:
        raise ActorNotAllowedError(
            actor, f"transition from {current_status!r} to {target_status!r}"
        )

    return edge
