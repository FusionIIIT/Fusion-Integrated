"""Tests for Complaint Management domain logic and state transitions.

Pure Python tests; no database access required.
"""
import pytest

from modules.complaints.domain.errors import InvalidComplaintTransition
from modules.complaints.domain.state_machine import (
    ComplaintPriority,
    ComplaintStatus,
    EscalationType,
    TRANSITIONS,
    validate_transition,
)


def test_valid_lifecycle_transitions():
    # Submitted -> In Progress
    validate_transition(
        ComplaintStatus.SUBMITTED,
        ComplaintStatus.IN_PROGRESS,
        permissions={"complaints.complaint.update"},
    )
    # In Progress -> Resolved
    validate_transition(
        ComplaintStatus.IN_PROGRESS,
        ComplaintStatus.RESOLVED,
        permissions={"complaints.complaint.resolve"},
    )
    # Resolved -> Closed
    validate_transition(
        ComplaintStatus.RESOLVED,
        ComplaintStatus.CLOSED,
        permissions={"complaints.complaint.close"},
    )
    # Submitted -> Rejected
    validate_transition(
        ComplaintStatus.SUBMITTED,
        ComplaintStatus.REJECTED,
        permissions={"complaints.complaint.resolve"},
    )
    # Closed -> In Progress (Reopening)
    validate_transition(
        ComplaintStatus.CLOSED,
        ComplaintStatus.IN_PROGRESS,
        permissions={"complaints.complaint.supervise"},
    )


def test_illegal_transitions_raise_error():
    # Cannot jump from Submitted directly to Closed
    with pytest.raises(InvalidComplaintTransition):
        validate_transition(
            ComplaintStatus.SUBMITTED,
            ComplaintStatus.CLOSED,
            permissions={"*"},
        )

    # Cannot transition from Rejected to Resolved (Rejected is terminal)
    with pytest.raises(InvalidComplaintTransition):
        validate_transition(
            ComplaintStatus.REJECTED,
            ComplaintStatus.RESOLVED,
            permissions={"*"},
        )


def test_permission_enforcement():
    with pytest.raises(InvalidComplaintTransition, match="lacks required permission"):
        validate_transition(
            ComplaintStatus.SUBMITTED,
            ComplaintStatus.IN_PROGRESS,
            permissions={"unrelated.permission"},
        )


def test_wildcard_permission_passes():
    validate_transition(
        ComplaintStatus.SUBMITTED,
        ComplaintStatus.IN_PROGRESS,
        permissions={"*"},
    )
