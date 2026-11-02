"""Domain layer unit tests: pure Python, zero DB, lightning fast execution."""

import pytest

from modules.hostel.domain.constants import (
    AllotmentStatus,
    ComplaintStatus,
    ExtendedStayStatus,
    GuestRoomBookingStatus,
    LeaveStatus,
)
from modules.hostel.domain.errors import InvalidTransitionError
from modules.hostel.domain.state_machine import (
    ALLOTMENT_TRANSITIONS,
    COMPLAINT_TRANSITIONS,
    EXTENDED_STAY_TRANSITIONS,
    GUEST_ROOM_TRANSITIONS,
    LEAVE_TRANSITIONS,
    can_transition,
    validate_transition,
)


def test_leave_state_machine_valid_flows():
    """BR-HM-012..014: Test legal leave transitions."""
    # Caretaker approves pending leave
    t = validate_transition(
        LEAVE_TRANSITIONS, LeaveStatus.PENDING, LeaveStatus.APPROVED, actor_role="caretaker"
    )
    assert t.to == LeaveStatus.APPROVED

    # Caretaker rejects pending leave
    t = validate_transition(
        LEAVE_TRANSITIONS, LeaveStatus.PENDING, LeaveStatus.REJECTED, actor_role="caretaker"
    )
    assert t.to == LeaveStatus.REJECTED

    # Student cancels pending leave
    t = validate_transition(
        LEAVE_TRANSITIONS, LeaveStatus.PENDING, LeaveStatus.CANCELLED, actor_role="student"
    )
    assert t.to == LeaveStatus.CANCELLED


def test_leave_state_machine_unauthorized_role():
    """Student cannot approve leaves."""
    with pytest.raises(InvalidTransitionError):
        validate_transition(
            LEAVE_TRANSITIONS, LeaveStatus.PENDING, LeaveStatus.APPROVED, actor_role="student"
        )


def test_leave_state_machine_illegal_transition():
    """Cannot jump from approved to rejected."""
    with pytest.raises(InvalidTransitionError):
        validate_transition(
            LEAVE_TRANSITIONS, LeaveStatus.APPROVED, LeaveStatus.REJECTED, actor_role="caretaker"
        )


def test_complaint_state_machine_escalation_and_resolution():
    """BR-HM-015..017: Test complaint lifecycle."""
    # Caretaker moves open -> in_progress
    t = validate_transition(
        COMPLAINT_TRANSITIONS,
        ComplaintStatus.OPEN,
        ComplaintStatus.IN_PROGRESS,
        actor_role="caretaker",
    )
    assert t.to == ComplaintStatus.IN_PROGRESS

    # Caretaker escalates to warden
    t = validate_transition(
        COMPLAINT_TRANSITIONS,
        ComplaintStatus.IN_PROGRESS,
        ComplaintStatus.ESCALATED,
        actor_role="caretaker",
    )
    assert t.to == ComplaintStatus.ESCALATED

    # Warden resolves escalated complaint
    t = validate_transition(
        COMPLAINT_TRANSITIONS,
        ComplaintStatus.ESCALATED,
        ComplaintStatus.RESOLVED,
        actor_role="warden",
    )
    assert t.to == ComplaintStatus.RESOLVED

    # Student reopens resolved complaint
    t = validate_transition(
        COMPLAINT_TRANSITIONS,
        ComplaintStatus.RESOLVED,
        ComplaintStatus.OPEN,
        actor_role="student",
    )
    assert t.to == ComplaintStatus.OPEN


def test_complaint_illegal_transition():
    with pytest.raises(InvalidTransitionError):
        validate_transition(
            COMPLAINT_TRANSITIONS, ComplaintStatus.RESOLVED, ComplaintStatus.ESCALATED
        )


def test_guest_room_booking_transitions():
    """BR-HM-018, 019: Test guest room booking approval and check-in."""
    # Caretaker approves booking
    t = validate_transition(
        GUEST_ROOM_TRANSITIONS,
        GuestRoomBookingStatus.PENDING,
        GuestRoomBookingStatus.APPROVED,
        actor_role="caretaker",
    )
    assert t.to == GuestRoomBookingStatus.APPROVED

    # Caretaker checks in
    t = validate_transition(
        GUEST_ROOM_TRANSITIONS,
        GuestRoomBookingStatus.APPROVED,
        GuestRoomBookingStatus.CHECKED_IN,
        actor_role="caretaker",
    )
    assert t.to == GuestRoomBookingStatus.CHECKED_IN

    # Caretaker checks out
    t = validate_transition(
        GUEST_ROOM_TRANSITIONS,
        GuestRoomBookingStatus.CHECKED_IN,
        GuestRoomBookingStatus.CHECKED_OUT,
        actor_role="caretaker",
    )
    assert t.to == GuestRoomBookingStatus.CHECKED_OUT


def test_extended_stay_transitions():
    """BR-HM-020..024: Extended stay approvals."""
    t = validate_transition(
        EXTENDED_STAY_TRANSITIONS,
        ExtendedStayStatus.PENDING,
        ExtendedStayStatus.APPROVED,
        actor_role="warden",
    )
    assert t.to == ExtendedStayStatus.APPROVED

    t = validate_transition(
        EXTENDED_STAY_TRANSITIONS,
        ExtendedStayStatus.PENDING,
        ExtendedStayStatus.REJECTED,
        actor_role="warden",
    )
    assert t.to == ExtendedStayStatus.REJECTED


def test_allotment_transitions():
    """BR-HM-008..010: Room allotment lifecycle."""
    t = validate_transition(ALLOTMENT_TRANSITIONS, AllotmentStatus.ACTIVE, AllotmentStatus.VACATED)
    assert t.to == AllotmentStatus.VACATED


def test_can_transition_helper():
    assert can_transition(LEAVE_TRANSITIONS, LeaveStatus.PENDING, LeaveStatus.APPROVED) is True
    assert can_transition(LEAVE_TRANSITIONS, LeaveStatus.APPROVED, LeaveStatus.PENDING) is False
