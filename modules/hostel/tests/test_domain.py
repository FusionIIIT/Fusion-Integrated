"""Domain unit tests for hostel: pure Python, milliseconds.

Cites: BR-HM-010, BR-HM-025, BR-HM-029, BW-HM-02, BW-HM-03, BW-HM-04, BW-HM-05.
"""
import pytest

from modules.hostel.domain.policies import (
    PolicyViolationError,
    validate_fine_amount,
    validate_notice_topic,
    validate_room_capacity,
)
from modules.hostel.domain.state_machines import (
    InvalidTransitionError,
    apply_complaint_transition,
    apply_leave_transition,
)


def test_validate_room_capacity_boundary():
    # BR-HM-010: Room Capacity Limit Enforcement
    validate_room_capacity(1, 2)
    with pytest.raises(PolicyViolationError, match="capacity limit reached"):
        validate_room_capacity(2, 2)


def test_validate_fine_amount_strictly_positive():
    # BR-HM-025: Fine Mandatory Data Fields & positive amount
    validate_fine_amount(100.0)
    with pytest.raises(PolicyViolationError, match="greater than zero"):
        validate_fine_amount(0)
    with pytest.raises(PolicyViolationError, match="greater than zero"):
        validate_fine_amount(-50.0)


def test_validate_notice_topic_whitelist():
    # BR-HM-029: Assigned-Hostel Notice Publishing
    validate_notice_topic("general")
    validate_notice_topic("maintenance")
    with pytest.raises(PolicyViolationError, match="Invalid notice topic"):
        validate_notice_topic("unauthorized_topic")


def test_leave_state_machine_transitions():
    # BW-HM-02: Leave Approval Path
    assert apply_leave_transition("PENDING", "approve", "caretaker") == "APPROVED"
    # BW-HM-03: Leave Rejection Path
    assert apply_leave_transition("PENDING", "reject", "caretaker") == "REJECTED"
    # Student cancellation
    assert apply_leave_transition("PENDING", "cancel", "student") == "CANCELLED"
    # Illegal transitions
    with pytest.raises(InvalidTransitionError):
        apply_leave_transition("APPROVED", "reject", "caretaker")


def test_complaint_state_machine_transitions():
    # BW-HM-04: Complaint Resolution Path
    assert apply_complaint_transition("LOGGED", "start_review", "caretaker") == "IN_PROGRESS"
    assert apply_complaint_transition("IN_PROGRESS", "resolve", "caretaker") == "RESOLVED"
    # BW-HM-05: Complaint Escalation Path
    assert apply_complaint_transition("IN_PROGRESS", "escalate", "caretaker") == "ESCALATED"
    assert apply_complaint_transition("ESCALATED", "resolve", "warden") == "RESOLVED"
