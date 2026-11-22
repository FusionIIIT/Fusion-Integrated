"""Domain layer unit tests for Hostel Management (pure Python)."""

import unittest
from datetime import date
from decimal import Decimal

from modules.hostel.domain.enums import (
    AccommodationRequestStatus,
    ComplaintCategory,
    ComplaintStatus,
    ExtendedStayStatus,
    GuestRoomBookingStatus,
    LeaveStatus,
)
from modules.hostel.domain.errors import (
    CapacityExceededError,
    InvalidStateTransitionError,
    MandatoryFieldMissingError,
    NoticePermissionError,
    ScopeBoundaryError,
    UnauthorizedHostelAccessError,
)
from modules.hostel.domain.rules import (
    validate_caretaker_access,
    validate_complaint_data,
    validate_fine_fields,
    validate_notice_publication,
    validate_room_capacity,
    validate_student_access,
)
from modules.hostel.domain.state_machine import (
    transition_accommodation_request,
    transition_complaint,
    transition_extended_stay,
    transition_guest_room_booking,
    transition_leave_request,
)


class RoomCapacityRuleTests(unittest.TestCase):
    """Enforces BR-HM-010: room capacity limit enforcement."""

    def test_within_capacity_passes(self):
        validate_room_capacity(current_occupancy=1, room_capacity=2, adding=1)

    def test_exceeding_capacity_raises(self):
        with self.assertRaises(CapacityExceededError):
            validate_room_capacity(current_occupancy=2, room_capacity=2, adding=1)


class FineValidationRuleTests(unittest.TestCase):
    """Enforces BR-HM-025: mandatory fine data fields."""

    def test_valid_fine_passes(self):
        validate_fine_fields(
            student_user_id=101,
            amount=Decimal("250.00"),
            reason="Damaged hostel window pane",
            imposed_date=date(2026, 11, 20),
        )

    def test_missing_student_raises(self):
        with self.assertRaises(MandatoryFieldMissingError):
            validate_fine_fields(None, Decimal("100"), "Reason", date.today())

    def test_invalid_amount_raises(self):
        with self.assertRaises(MandatoryFieldMissingError):
            validate_fine_fields(101, Decimal("0"), "Reason", date.today())

    def test_missing_reason_raises(self):
        with self.assertRaises(MandatoryFieldMissingError):
            validate_fine_fields(101, Decimal("100"), "", date.today())


class ComplaintValidationRuleTests(unittest.TestCase):
    """Enforces BR-HM-015 and BR-HM-016: complaint core data and hostel scope."""

    def test_valid_complaint_passes(self):
        validate_complaint_data(ComplaintCategory.ELECTRICAL.value, "Fan not spinning in room")

    def test_missing_category_raises(self):
        with self.assertRaises(MandatoryFieldMissingError):
            validate_complaint_data("", "Description")

    def test_out_of_scope_category_raises(self):
        with self.assertRaises(ScopeBoundaryError):
            validate_complaint_data("academic_grading_dispute", "Description")


class AccessRulesTests(unittest.TestCase):
    """Enforces BR-HM-002, BR-HM-029, BR-HM-035."""

    def test_notice_publishing_for_assigned_hostel_passes(self):
        validate_notice_publication([1, 2], target_hostel_id=1)

    def test_notice_publishing_for_unassigned_hostel_raises(self):
        with self.assertRaises(NoticePermissionError):
            validate_notice_publication([1, 2], target_hostel_id=3)

    def test_caretaker_access_to_assigned_hostel_passes(self):
        validate_caretaker_access([1, 2], target_hostel_id=2)

    def test_caretaker_access_to_unassigned_hostel_raises(self):
        with self.assertRaises(UnauthorizedHostelAccessError):
            validate_caretaker_access([1, 2], target_hostel_id=5)

    def test_student_access_matches_hostel(self):
        validate_student_access(1, 1)
        with self.assertRaises(UnauthorizedHostelAccessError):
            validate_student_access(1, 2)


class StateMachineTests(unittest.TestCase):
    """Enforces Authoritative State Transitions for Workflows."""

    def test_accommodation_request_workflow(self):
        res = transition_accommodation_request(
            AccommodationRequestStatus.SUBMITTED.value, AccommodationRequestStatus.ALLOTTED.value
        )
        self.assertEqual(res, AccommodationRequestStatus.ALLOTTED.value)

    def test_leave_request_workflow(self):
        approved = transition_leave_request(LeaveStatus.SUBMITTED.value, LeaveStatus.APPROVED.value)
        self.assertEqual(approved, LeaveStatus.APPROVED.value)
        rejected = transition_leave_request(LeaveStatus.SUBMITTED.value, LeaveStatus.REJECTED.value)
        self.assertEqual(rejected, LeaveStatus.REJECTED.value)
        with self.assertRaises(InvalidStateTransitionError):
            transition_leave_request(LeaveStatus.APPROVED.value, LeaveStatus.REJECTED.value)

    def test_complaint_workflow(self):
        # Submitted -> Resolved
        self.assertEqual(
            transition_complaint(ComplaintStatus.SUBMITTED.value, ComplaintStatus.RESOLVED.value),
            ComplaintStatus.RESOLVED.value,
        )
        # Submitted -> Escalated
        self.assertEqual(
            transition_complaint(ComplaintStatus.SUBMITTED.value, ComplaintStatus.ESCALATED.value),
            ComplaintStatus.ESCALATED.value,
        )
        # Escalated -> Resolved
        self.assertEqual(
            transition_complaint(ComplaintStatus.ESCALATED.value, ComplaintStatus.RESOLVED.value),
            ComplaintStatus.RESOLVED.value,
        )

    def test_guest_room_workflow(self):
        self.assertEqual(
            transition_guest_room_booking(
                GuestRoomBookingStatus.SUBMITTED.value, GuestRoomBookingStatus.APPROVED.value
            ),
            GuestRoomBookingStatus.APPROVED.value,
        )

    def test_extended_stay_workflow(self):
        self.assertEqual(
            transition_extended_stay(
                ExtendedStayStatus.SUBMITTED.value, ExtendedStayStatus.APPROVED.value
            ),
            ExtendedStayStatus.APPROVED.value,
        )
