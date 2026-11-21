"""Tests for Hostel domain models and state transitions."""

import pytest
from datetime import date
from django.db import IntegrityError
from modules.hostel.domain.constants import (
    AccommodationStatus,
    ComplaintStatus,
    ExtendedStayStatus,
    GuestRoomStatus,
    LeaveStatus,
)
from modules.hostel.domain.errors import (
    HostelDomainError,
    InvalidStateTransitionError,
    RoomCapacityExceededError,
)
from modules.hostel.domain.state_machine import WorkflowStateMachine
from modules.hostel.models import Hostel, Room


@pytest.mark.django_db
def test_hostel_creation_and_uniqueness():
    h1 = Hostel.objects.create(name="Hall of Residence 1", code="H1", capacity=100)
    assert h1.is_active is True
    assert str(h1) == "Hall of Residence 1 (H1)"

    # Duplicate code should fail
    with pytest.raises(IntegrityError):
        Hostel.objects.create(name="Another Hall", code="H1")


@pytest.mark.django_db
def test_room_uniqueness_within_hostel():
    h = Hostel.objects.create(name="Hall 3", code="H3", capacity=100)
    Room.objects.create(hostel=h, room_number="101", capacity=2)

    # Same room number in same hostel should fail
    with pytest.raises(IntegrityError):
        Room.objects.create(hostel=h, room_number="101", capacity=3)


def test_accommodation_workflow_transitions():
    # Valid
    WorkflowStateMachine.validate_accommodation_transition(
        AccommodationStatus.SUBMITTED.value, AccommodationStatus.ALLOTTED.value
    )
    WorkflowStateMachine.validate_accommodation_transition(
        AccommodationStatus.SUBMITTED.value, AccommodationStatus.REJECTED.value
    )

    # Invalid
    with pytest.raises(InvalidStateTransitionError):
        WorkflowStateMachine.validate_accommodation_transition(
            AccommodationStatus.ALLOTTED.value, AccommodationStatus.SUBMITTED.value
        )


def test_leave_workflow_transitions():
    WorkflowStateMachine.validate_leave_transition(
        LeaveStatus.SUBMITTED.value, LeaveStatus.APPROVED.value
    )
    WorkflowStateMachine.validate_leave_transition(
        LeaveStatus.SUBMITTED.value, LeaveStatus.REJECTED.value
    )

    with pytest.raises(InvalidStateTransitionError):
        WorkflowStateMachine.validate_leave_transition(
            LeaveStatus.APPROVED.value, LeaveStatus.REJECTED.value
        )


def test_complaint_workflow_transitions():
    WorkflowStateMachine.validate_complaint_transition(
        ComplaintStatus.SUBMITTED.value, ComplaintStatus.IN_PROGRESS.value
    )
    WorkflowStateMachine.validate_complaint_transition(
        ComplaintStatus.SUBMITTED.value, ComplaintStatus.ESCALATED.value
    )
    WorkflowStateMachine.validate_complaint_transition(
        ComplaintStatus.ESCALATED.value, ComplaintStatus.RESOLVED.value
    )

    with pytest.raises(InvalidStateTransitionError):
        WorkflowStateMachine.validate_complaint_transition(
            ComplaintStatus.RESOLVED.value, ComplaintStatus.SUBMITTED.value
        )


def test_guest_room_workflow_transitions():
    WorkflowStateMachine.validate_guest_room_transition(
        GuestRoomStatus.REQUESTED.value, GuestRoomStatus.APPROVED.value
    )
    WorkflowStateMachine.validate_guest_room_transition(
        GuestRoomStatus.REQUESTED.value, GuestRoomStatus.REJECTED.value
    )

    with pytest.raises(InvalidStateTransitionError):
        WorkflowStateMachine.validate_guest_room_transition(
            GuestRoomStatus.REJECTED.value, GuestRoomStatus.APPROVED.value
        )


def test_extended_stay_workflow_transitions():
    WorkflowStateMachine.validate_extended_stay_transition(
        ExtendedStayStatus.SUBMITTED.value, ExtendedStayStatus.APPROVED.value
    )
    WorkflowStateMachine.validate_extended_stay_transition(
        ExtendedStayStatus.SUBMITTED.value, ExtendedStayStatus.REJECTED.value
    )

    with pytest.raises(InvalidStateTransitionError):
        WorkflowStateMachine.validate_extended_stay_transition(
            ExtendedStayStatus.APPROVED.value, ExtendedStayStatus.SUBMITTED.value
        )
