"""Declarative State Machine and Transition Rules for CMS (BW-CMS-01 to BW-CMS-08).

Pure Python with zero framework dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

from .entities import ComplaintStatus, TERMINAL_STATUSES
from .errors import InvalidTransition, RuleViolation


@dataclass(frozen=True)
class Transition:
    frm: ComplaintStatus
    to: ComplaintStatus
    permission: str
    description: str = ""


# Authoritative lifecycle transitions
LEGAL_TRANSITIONS: tuple[Transition, ...] = (
    # Intake / Setup -> In Progress
    Transition(
        ComplaintStatus.SUBMITTED,
        ComplaintStatus.IN_PROGRESS,
        permission="complaints.complaint.update",
        description="Handler assigns worker or updates progress",
    ),
    # Direct resolution from Submitted
    Transition(
        ComplaintStatus.SUBMITTED,
        ComplaintStatus.RESOLVED,
        permission="complaints.complaint.resolve",
        description="Handler resolves complaint directly",
    ),
    # Rejection from Submitted
    Transition(
        ComplaintStatus.SUBMITTED,
        ComplaintStatus.REJECTED,
        permission="complaints.complaint.reject",
        description="Handler rejects complaint with reason",
    ),
    # Progress -> Resolved
    Transition(
        ComplaintStatus.IN_PROGRESS,
        ComplaintStatus.RESOLVED,
        permission="complaints.complaint.resolve",
        description="Handler resolves complaint with resolution details",
    ),
    # Progress -> Rejected
    Transition(
        ComplaintStatus.IN_PROGRESS,
        ComplaintStatus.REJECTED,
        permission="complaints.complaint.reject",
        description="Handler rejects complaint with reason",
    ),
    # Resolved -> Closed (User or Supervisor verification)
    Transition(
        ComplaintStatus.RESOLVED,
        ComplaintStatus.CLOSED,
        permission="complaints.complaint.verify",
        description="Verification successful by Complainant or Supervisor",
    ),
    # Closed -> In Progress (Reopening Approved)
    Transition(
        ComplaintStatus.CLOSED,
        ComplaintStatus.IN_PROGRESS,
        permission="complaints.complaint.reopen",
        description="Supervisor approves reopening request",
    ),
)


def validate_transition(
    current_status: ComplaintStatus | str,
    target_status: ComplaintStatus | str,
    *,
    permissions: Sequence[str] | set[str] | None = None,
    resolution_details: str = "",
    rejection_reason: str = "",
) -> Transition:
    """Validate that moving from current_status to target_status is legal.

    Raises InvalidTransition or RuleViolation if illegal.
    """
    curr = ComplaintStatus(current_status)
    tgt = ComplaintStatus(target_status)

    if curr == tgt:
        raise InvalidTransition(curr, tgt, reason="Current and target states are identical.")

    # Find matching transition
    matching = [t for t in LEGAL_TRANSITIONS if t.frm == curr and t.to == tgt]
    if not matching:
        raise InvalidTransition(curr, tgt, reason="No legal path exists between these states.")

    trans = matching[0]

    if permissions is not None and "*" not in permissions:
        if trans.permission not in permissions:
            raise RuleViolation(
                f"Missing required permission '{trans.permission}' for transition {curr} -> {tgt}.",
                code="permission_denied",
            )

    # Business rule guards
    if tgt == ComplaintStatus.RESOLVED and not resolution_details.strip():
        raise RuleViolation(
            "Resolution details are required to resolve a complaint (BR-CMS-013).",
            code="resolution_details_required",
        )

    if tgt == ComplaintStatus.REJECTED and not rejection_reason.strip():
        raise RuleViolation(
            "Rejection reason is required to reject a complaint (BR-CMS-014).",
            code="rejection_reason_required",
        )

    return trans

