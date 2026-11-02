"""State machine and lifecycle definitions for Complaint Management System.

Authoritative State-Transition Table (STT) implementation per:
- BW-CMS-01: Complaint Intake to Resolved
- BW-CMS-02: Complaint Intake to User-Verified Closure
- BW-CMS-03: Complaint Intake to Supervisor-Verified Closure
- BW-CMS-04: Complaint Intake to Rejection
- BW-CMS-05: Reopening Request Denied
- BW-CMS-06: Reopening Request Approved
- BW-CMS-07: Manual Escalation of Unresolved Complaint
- BW-CMS-08: Automatic SLA Escalation
"""
from dataclasses import dataclass
from enum import StrEnum
from typing import Set

from .errors import InvalidComplaintTransition


class ComplaintStatus(StrEnum):
    SUBMITTED = "submitted"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    REJECTED = "rejected"
    CLOSED = "closed"


class ComplaintPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EscalationType(StrEnum):
    NONE = "none"
    MANUAL = "manual"
    AUTOMATIC_SLA = "automatic_sla"


class ClosureVerification(StrEnum):
    NONE = "none"
    USER = "user"
    SUPERVISOR = "supervisor"


class ReopeningStatus(StrEnum):
    NONE = "none"
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"


@dataclass(frozen=True)
class Transition:
    frm: ComplaintStatus
    to: ComplaintStatus
    permission: str
    description: str


TRANSITIONS: tuple[Transition, ...] = (
    # Handler assigns / updates progress
    Transition(
        ComplaintStatus.SUBMITTED,
        ComplaintStatus.IN_PROGRESS,
        permission="complaints.complaint.update",
        description="Handler begins operational processing",
    ),
    # Handler resolves directly from submitted or in_progress
    Transition(
        ComplaintStatus.SUBMITTED,
        ComplaintStatus.RESOLVED,
        permission="complaints.complaint.resolve",
        description="Handler resolves submitted complaint",
    ),
    Transition(
        ComplaintStatus.IN_PROGRESS,
        ComplaintStatus.RESOLVED,
        permission="complaints.complaint.resolve",
        description="Handler resolves in-progress complaint",
    ),
    # Handler rejects with mandatory reason
    Transition(
        ComplaintStatus.SUBMITTED,
        ComplaintStatus.REJECTED,
        permission="complaints.complaint.resolve",
        description="Handler rejects submitted complaint with reason",
    ),
    Transition(
        ComplaintStatus.IN_PROGRESS,
        ComplaintStatus.REJECTED,
        permission="complaints.complaint.resolve",
        description="Handler rejects in-progress complaint with reason",
    ),
    # Closure after resolution (direct or after verification)
    Transition(
        ComplaintStatus.RESOLVED,
        ComplaintStatus.CLOSED,
        permission="complaints.complaint.close",
        description="Complaint verified and closed (by user or supervisor) or direct closure",
    ),
    # Approved reopening returns complaint to in_progress
    Transition(
        ComplaintStatus.CLOSED,
        ComplaintStatus.IN_PROGRESS,
        permission="complaints.complaint.supervise",
        description="Supervisor approves reopening request, returning complaint to handling",
    ),
)

TERMINAL_STATES: Set[ComplaintStatus] = {ComplaintStatus.REJECTED}


def validate_transition(
    from_status: str,
    to_status: str,
    permissions: Set[str] | None = None,
    *,
    reason: str = "",
) -> None:
    """Validate that moving from `from_status` to `to_status` is legal and permitted."""
    try:
        frm = ComplaintStatus(from_status)
        to = ComplaintStatus(to_status)
    except ValueError as exc:
        raise InvalidComplaintTransition(from_status, to_status, f"Unknown status: {exc}") from exc

    matching = [t for t in TRANSITIONS if t.frm == frm and t.to == to]
    if not matching:
        raise InvalidComplaintTransition(
            from_status,
            to_status,
            f"No legal transition defined from '{from_status}' to '{to_status}'.",
        )

    if permissions is not None and "*" not in permissions:
        required_perm = matching[0].permission
        if required_perm not in permissions:
            raise InvalidComplaintTransition(
                from_status,
                to_status,
                f"Caller lacks required permission '{required_perm}'.",
            )
