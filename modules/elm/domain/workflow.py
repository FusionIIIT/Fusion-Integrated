"""Core Employee Leave Management workflow rules."""

from enum import StrEnum


class LeaveStatus(StrEnum):
    DRAFT = "draft"
    PENDING_SUBSTITUTE = "pending_substitute"
    PENDING_UNIT_HEAD = "pending_unit_head"
    PENDING_ESTABLISHMENT = "pending_establishment"
    PENDING_SANCTION = "pending_sanction"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    CANCELLED = "cancelled"


# Only explicitly permitted lifecycle transitions are allowed.
TRANSITIONS = {
    LeaveStatus.DRAFT: {LeaveStatus.PENDING_SUBSTITUTE},
    LeaveStatus.PENDING_SUBSTITUTE: {
        LeaveStatus.PENDING_UNIT_HEAD,
        LeaveStatus.WITHDRAWN,
    },
    LeaveStatus.PENDING_UNIT_HEAD: {
        LeaveStatus.PENDING_ESTABLISHMENT,
        LeaveStatus.PENDING_SANCTION,
        LeaveStatus.APPROVED,
        LeaveStatus.REJECTED,
        LeaveStatus.WITHDRAWN,
    },
    LeaveStatus.PENDING_ESTABLISHMENT: {
        LeaveStatus.PENDING_SANCTION,
        LeaveStatus.REJECTED,
        LeaveStatus.WITHDRAWN,
    },
    LeaveStatus.PENDING_SANCTION: {
        LeaveStatus.APPROVED,
        LeaveStatus.REJECTED,
        LeaveStatus.WITHDRAWN,
    },
    LeaveStatus.APPROVED: {LeaveStatus.CANCELLED},
    LeaveStatus.REJECTED: set(),
    LeaveStatus.WITHDRAWN: set(),
    LeaveStatus.CANCELLED: set(),
}


class InvalidTransition(ValueError):
    """Raised when a leave request attempts an invalid status change."""


def transition(current: LeaveStatus, target: LeaveStatus) -> LeaveStatus:
    """Validate a lifecycle transition and return the resulting status."""
    if target not in TRANSITIONS[current]:
        raise InvalidTransition(
            f"Cannot transition leave from '{current}' to '{target}'."
        )
    return target


def can_cancel_approved_leave(
    status: LeaveStatus, start_date, today
) -> bool:
    """Approved leave can be cancelled only before its start date."""
    return status == LeaveStatus.APPROVED and today < start_date
