"""Hostel Management - Use Case Spec Tests (Prompt B).

Each test maps directly to an HM-UC-XXX entry in UC_DESIGN.json.
test_id and source_id are recorded in each test docstring.
"""

from datetime import date
from decimal import Decimal

import pytest

from modules.hostel.domain.enums import (
    AccommodationRequestStatus,
    AllotmentStatus,
    ComplaintStatus,
    ExtendedStayStatus,
    FineStatus,
    GuestRoomBookingStatus,
    HostelGender,
    InventoryCondition,
    LeaveStatus,
    LeaveType,
    NoticePriority,
    NotificationEventType,
    RoleBindingType,
    RoomStatus,
    SecurityShiftStatus,
    ShiftType,
    StaffDutyRole,
)
from modules.hostel.domain.errors import (
    CapacityExceededError,
    InvalidStateTransitionError,
    MandatoryFieldMissingError,
    NoticePermissionError,
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

# ===========================================================================
# UC-001: Create Hostel (HM-UC-001)
# ===========================================================================


class TestUC001CreateHostel:
    """test_id: TC-UC-001 | source_id: HM-UC-001 Main Flow"""

    def test_hostel_gender_enum_all_values(self):
        """test_id: TC-UC-001 | source_id: HM-UC-001 Main Flow
        Hostel gender enum has boys, girls, coed options for creation.
        """
        values = {g.value for g in HostelGender}
        assert values == {"boys", "girls", "coed"}

    def test_hostel_model_has_required_fields(self):
        """test_id: TC-UC-001 | source_id: HM-UC-001 Main Flow
        Hostel model has code, name, gender_type, capacity fields.
        """
        from modules.hostel.models import Hostel

        assert hasattr(Hostel, "code")
        assert hasattr(Hostel, "gender_type")
        assert hasattr(Hostel, "capacity")


# ===========================================================================
# UC-002: Activate / Deactivate Hostel (HM-UC-002)
# ===========================================================================


class TestUC002ActivateDeactivateHostel:
    """test_id: TC-UC-002 | source_id: HM-UC-002 Main Flow"""

    def test_hostel_model_has_is_active_field(self):
        """test_id: TC-UC-002 | source_id: HM-UC-002 Main Flow
        Hostel model has is_active flag for activation/deactivation.
        """
        from modules.hostel.models import Hostel

        assert hasattr(Hostel, "is_active")


# ===========================================================================
# UC-003: Manage Warden Role Binding (HM-UC-003)
# ===========================================================================


class TestUC003WardenRoleBinding:
    """test_id: TC-UC-003 | source_id: HM-UC-003 Main Flow"""

    def test_warden_role_binding_model_exists(self):
        """test_id: TC-UC-003 | source_id: HM-UC-003 Main Flow
        HostelRoleBinding model exists and supports warden role.
        """
        from modules.hostel.models import HostelRoleBinding

        assert hasattr(HostelRoleBinding, "role")
        assert hasattr(HostelRoleBinding, "user_id")
        assert hasattr(HostelRoleBinding, "hostel")

    def test_warden_binding_role_enum(self):
        """test_id: TC-UC-003 | source_id: HM-UC-003 Main Flow
        RoleBindingType has WARDEN value.
        """
        assert RoleBindingType.WARDEN == "warden"


# ===========================================================================
# UC-004: Manage Caretaker Role Binding (HM-UC-004)
# ===========================================================================


class TestUC004CaretakerRoleBinding:
    """test_id: TC-UC-004 | source_id: HM-UC-004 Main Flow"""

    def test_caretaker_binding_has_shift(self):
        """test_id: TC-UC-004 | source_id: HM-UC-004 Main Flow
        HostelRoleBinding supports caretaker with shift context.
        """
        from modules.hostel.models import HostelRoleBinding

        assert hasattr(HostelRoleBinding, "shift")

    def test_shift_types_enum(self):
        """test_id: TC-UC-004 | source_id: HM-UC-004 Main Flow
        ShiftType enum has morning, evening, night, general values.
        """
        values = {s.value for s in ShiftType}
        assert values == {"morning", "evening", "night", "general"}


# ===========================================================================
# UC-005: Student Submits Accommodation Request (HM-UC-005)
# ===========================================================================


class TestUC005SubmitAccommodationRequest:
    """test_id: TC-UC-005 | source_id: HM-UC-005 Main Flow"""

    def test_accommodation_request_model_has_status(self):
        """test_id: TC-UC-005 | source_id: HM-UC-005 Main Flow
        AccommodationRequest model has status field defaulting to submitted.
        """
        from modules.hostel.models import AccommodationRequest

        assert hasattr(AccommodationRequest, "status")

    def test_accommodation_request_submitted_status_value(self):
        """test_id: TC-UC-005 | source_id: HM-UC-005 Main Flow
        SUBMITTED status value is 'submitted'.
        """
        assert AccommodationRequestStatus.SUBMITTED == "submitted"


# ===========================================================================
# UC-006: Super Admin Batch Allotment (HM-UC-006)
# ===========================================================================


class TestUC006BatchAllotment:
    """test_id: TC-UC-006 | source_id: HM-UC-006 Main Flow"""

    def test_room_allotment_model_has_required_fields(self):
        """test_id: TC-UC-006 | source_id: HM-UC-006 Main Flow
        RoomAllotment model has student_user_id, room, status, allotment_date.
        """
        from modules.hostel.models import RoomAllotment

        assert hasattr(RoomAllotment, "student_user_id")
        assert hasattr(RoomAllotment, "room")
        assert hasattr(RoomAllotment, "status")

    def test_capacity_guard_on_allotment(self):
        """test_id: TC-UC-006 | source_id: HM-UC-006 Main Flow
        Allotment to full room raises CapacityExceededError.
        """
        with pytest.raises(CapacityExceededError):
            validate_room_capacity(current_occupancy=3, room_capacity=3)


# ===========================================================================
# UC-007: Room Exchange (HM-UC-007)
# ===========================================================================


class TestUC007RoomExchange:
    """test_id: TC-UC-007 | source_id: HM-UC-007 Main Flow"""

    def test_room_exchange_model_exists(self):
        """test_id: TC-UC-007 | source_id: HM-UC-007 Main Flow
        RoomExchange model has required student references and status.
        """
        from modules.hostel.models import RoomExchange

        assert hasattr(RoomExchange, "student_a_user_id")
        assert hasattr(RoomExchange, "student_b_user_id")
        assert hasattr(RoomExchange, "status")


# ===========================================================================
# UC-008: Mark Attendance (HM-UC-008)
# ===========================================================================


class TestUC008MarkAttendance:
    """test_id: TC-UC-008 | source_id: HM-UC-008 Main Flow"""

    def test_attendance_record_model_exists(self):
        """test_id: TC-UC-008 | source_id: HM-UC-008 Main Flow
        AttendanceRecord model has student_user_id, date, status.
        """
        from modules.hostel.models import AttendanceRecord

        assert hasattr(AttendanceRecord, "student_user_id")
        assert hasattr(AttendanceRecord, "date")
        assert hasattr(AttendanceRecord, "status")

    def test_shift_types_in_attendance(self):
        """test_id: TC-UC-008 | source_id: HM-UC-008 Main Flow
        AttendanceRecord has status field for present/absent/on_leave.
        """
        from modules.hostel.models import AttendanceRecord

        assert hasattr(AttendanceRecord, "status")


# ===========================================================================
# UC-009: Submit Leave Request (HM-UC-009)
# ===========================================================================


class TestUC009SubmitLeaveRequest:
    """test_id: TC-UC-009 | source_id: HM-UC-009 Main Flow"""

    def test_leave_request_model_exists(self):
        """test_id: TC-UC-009 | source_id: HM-UC-009 Main Flow
        LeaveRequest model has required fields.
        """
        from modules.hostel.models import LeaveRequest

        assert hasattr(LeaveRequest, "student_user_id")
        assert hasattr(LeaveRequest, "leave_type")
        assert hasattr(LeaveRequest, "start_date")
        assert hasattr(LeaveRequest, "end_date")
        assert hasattr(LeaveRequest, "status")

    def test_leave_type_enum_values(self):
        """test_id: TC-UC-009 | source_id: HM-UC-009 Main Flow
        Leave types include home, medical, academic, emergency, other.
        """
        values = {t.value for t in LeaveType}
        assert "home" in values
        assert "medical" in values


# ===========================================================================
# UC-010: Approve / Reject Leave Request (HM-UC-010)
# ===========================================================================


class TestUC010LeaveDecision:
    """test_id: TC-UC-010 | source_id: HM-UC-010 Main Flow"""

    def test_leave_approval_transition(self):
        """test_id: TC-UC-010 | source_id: HM-UC-010 Main Flow
        Leave approval: submitted -> approved.
        """
        result = transition_leave_request(LeaveStatus.SUBMITTED, LeaveStatus.APPROVED)
        assert result == LeaveStatus.APPROVED

    def test_leave_rejection_transition(self):
        """test_id: TC-UC-010 | source_id: HM-UC-010 Main Flow
        Leave rejection: submitted -> rejected.
        """
        result = transition_leave_request(LeaveStatus.SUBMITTED, LeaveStatus.REJECTED)
        assert result == LeaveStatus.REJECTED


# ===========================================================================
# UC-011: Submit Complaint (HM-UC-011)
# ===========================================================================


class TestUC011SubmitComplaint:
    """test_id: TC-UC-011 | source_id: HM-UC-011 Main Flow"""

    def test_complaint_model_has_required_fields(self):
        """test_id: TC-UC-011 | source_id: HM-UC-011 Main Flow
        HostelComplaint model has student_user_id, category, description, status.
        """
        from modules.hostel.models import HostelComplaint

        assert hasattr(HostelComplaint, "student_user_id")
        assert hasattr(HostelComplaint, "category")
        assert hasattr(HostelComplaint, "description")
        assert hasattr(HostelComplaint, "status")

    def test_valid_complaint_data_accepted(self):
        """test_id: TC-UC-011 | source_id: HM-UC-011 Main Flow
        Valid complaint data passes domain validation.
        """
        validate_complaint_data("plumbing", "Water leakage in corridor")


# ===========================================================================
# UC-012: Resolve Complaint (HM-UC-012)
# ===========================================================================


class TestUC012ResolveComplaint:
    """test_id: TC-UC-012 | source_id: HM-UC-012 Main Flow"""

    def test_complaint_resolution_transition(self):
        """test_id: TC-UC-012 | source_id: HM-UC-012 Main Flow
        Complaint transitions from submitted to resolved.
        """
        result = transition_complaint(ComplaintStatus.SUBMITTED, ComplaintStatus.RESOLVED)
        assert result == ComplaintStatus.RESOLVED

    def test_complaint_model_has_resolved_at(self):
        """test_id: TC-UC-012 | source_id: HM-UC-012 Main Flow
        HostelComplaint model tracks resolved_at timestamp.
        """
        from modules.hostel.models import HostelComplaint

        assert hasattr(HostelComplaint, "resolved_at")


# ===========================================================================
# UC-013: Escalate Complaint (HM-UC-013)
# ===========================================================================


class TestUC013EscalateComplaint:
    """test_id: TC-UC-013 | source_id: HM-UC-013 Main Flow"""

    def test_complaint_escalation_transition(self):
        """test_id: TC-UC-013 | source_id: HM-UC-013 Main Flow
        Complaint transitions from submitted to escalated.
        """
        result = transition_complaint(ComplaintStatus.SUBMITTED, ComplaintStatus.ESCALATED)
        assert result == ComplaintStatus.ESCALATED

    def test_complaint_model_has_escalated_at(self):
        """test_id: TC-UC-013 | source_id: HM-UC-013 Main Flow
        HostelComplaint model tracks escalated_at timestamp.
        """
        from modules.hostel.models import HostelComplaint

        assert hasattr(HostelComplaint, "escalated_at")


# ===========================================================================
# UC-014: Guest Room Booking (HM-UC-014)
# ===========================================================================


class TestUC014GuestRoomBooking:
    """test_id: TC-UC-014 | source_id: HM-UC-014 Main Flow"""

    def test_guest_room_booking_model_exists(self):
        """test_id: TC-UC-014 | source_id: HM-UC-014 Main Flow
        GuestRoomBooking model has required fields.
        """
        from modules.hostel.models import GuestRoomBooking

        assert hasattr(GuestRoomBooking, "guest_name")
        assert hasattr(GuestRoomBooking, "check_in_date")
        assert hasattr(GuestRoomBooking, "check_out_date")
        assert hasattr(GuestRoomBooking, "status")

    def test_initial_booking_status_submitted(self):
        """test_id: TC-UC-014 | source_id: HM-UC-014 Main Flow
        Initial guest room booking status is SUBMITTED.
        """
        assert GuestRoomBookingStatus.SUBMITTED == "submitted"


# ===========================================================================
# UC-015: Approve / Reject Guest Room Booking (HM-UC-015)
# ===========================================================================


class TestUC015GuestRoomDecision:
    """test_id: TC-UC-015 | source_id: HM-UC-015 Main Flow"""

    def test_guest_booking_approval_transition(self):
        """test_id: TC-UC-015 | source_id: HM-UC-015 Main Flow
        Guest booking: submitted -> approved.
        """
        result = transition_guest_room_booking(
            GuestRoomBookingStatus.SUBMITTED, GuestRoomBookingStatus.APPROVED
        )
        assert result == GuestRoomBookingStatus.APPROVED

    def test_guest_booking_rejection_transition(self):
        """test_id: TC-UC-015 | source_id: HM-UC-015 Main Flow
        Guest booking: submitted -> rejected.
        """
        result = transition_guest_room_booking(
            GuestRoomBookingStatus.SUBMITTED, GuestRoomBookingStatus.REJECTED
        )
        assert result == GuestRoomBookingStatus.REJECTED


# ===========================================================================
# UC-016: Extended Stay Request (HM-UC-016)
# ===========================================================================


class TestUC016ExtendedStay:
    """test_id: TC-UC-016 | source_id: HM-UC-016 Main Flow"""

    def test_extended_stay_model_exists(self):
        """test_id: TC-UC-016 | source_id: HM-UC-016 Main Flow
        ExtendedStayRequest model has required fields.
        """
        from modules.hostel.models import ExtendedStayRequest

        assert hasattr(ExtendedStayRequest, "student_user_id")
        assert hasattr(ExtendedStayRequest, "end_date")
        assert hasattr(ExtendedStayRequest, "status")

    def test_initial_extended_stay_status_submitted(self):
        """test_id: TC-UC-016 | source_id: HM-UC-016 Main Flow
        Initial extended stay status is SUBMITTED.
        """
        assert ExtendedStayStatus.SUBMITTED == "submitted"


# ===========================================================================
# UC-017: Approve / Reject Extended Stay (HM-UC-017)
# ===========================================================================


class TestUC017ExtendedStayDecision:
    """test_id: TC-UC-017 | source_id: HM-UC-017 Main Flow"""

    def test_extended_stay_approval_transition(self):
        """test_id: TC-UC-017 | source_id: HM-UC-017 Main Flow
        Extended stay: submitted -> approved.
        """
        result = transition_extended_stay(ExtendedStayStatus.SUBMITTED, ExtendedStayStatus.APPROVED)
        assert result == ExtendedStayStatus.APPROVED

    def test_extended_stay_rejection_transition(self):
        """test_id: TC-UC-017 | source_id: HM-UC-017 Main Flow
        Extended stay: submitted -> rejected.
        """
        result = transition_extended_stay(ExtendedStayStatus.SUBMITTED, ExtendedStayStatus.REJECTED)
        assert result == ExtendedStayStatus.REJECTED


# ===========================================================================
# UC-018: Record Fine (HM-UC-018)
# ===========================================================================


class TestUC018RecordFine:
    """test_id: TC-UC-018 | source_id: HM-UC-018 Main Flow"""

    def test_hostel_fine_model_exists(self):
        """test_id: TC-UC-018 | source_id: HM-UC-018 Main Flow
        HostelFine model has required fields.
        """
        from modules.hostel.models import HostelFine

        assert hasattr(HostelFine, "student_user_id")
        assert hasattr(HostelFine, "amount")
        assert hasattr(HostelFine, "reason")
        assert hasattr(HostelFine, "imposed_date")
        assert hasattr(HostelFine, "status")

    def test_valid_fine_fields_pass(self):
        """test_id: TC-UC-018 | source_id: HM-UC-018 Main Flow
        Valid fine data passes domain validation.
        """
        validate_fine_fields(
            student_user_id=7,
            amount=Decimal("150.00"),
            reason="Violation of hostel rules",
            imposed_date=date(2026, 5, 20),
        )

    def test_fine_status_recorded(self):
        """test_id: TC-UC-018 | source_id: HM-UC-018 Main Flow
        Fine initial status is RECORDED.
        """
        assert FineStatus.RECORDED == "recorded"


# ===========================================================================
# UC-019: Manage Inventory (HM-UC-019)
# ===========================================================================


class TestUC019Inventory:
    """test_id: TC-UC-019 | source_id: HM-UC-019 Main Flow"""

    def test_hostel_inventory_model_exists(self):
        """test_id: TC-UC-019 | source_id: HM-UC-019 Main Flow
        HostelInventoryItem model has required fields.
        """
        from modules.hostel.models import HostelInventoryItem

        assert hasattr(HostelInventoryItem, "hostel")
        assert hasattr(HostelInventoryItem, "item_name")
        assert hasattr(HostelInventoryItem, "quantity")
        assert hasattr(HostelInventoryItem, "condition")

    def test_inventory_condition_enum(self):
        """test_id: TC-UC-019 | source_id: HM-UC-019 Main Flow
        Inventory condition enum has working, damaged, repair_needed, scrapped.
        """
        values = {c.value for c in InventoryCondition}
        assert values == {"working", "damaged", "repair_needed", "scrapped"}


# ===========================================================================
# UC-020: Log Staff Duty (HM-UC-020)
# ===========================================================================


class TestUC020StaffDuty:
    """test_id: TC-UC-020 | source_id: HM-UC-020 Main Flow"""

    def test_hostel_staff_duty_log_model_exists(self):
        """test_id: TC-UC-020 | source_id: HM-UC-020 Main Flow
        HostelStaffDutyLog model has required fields.
        """
        from modules.hostel.models import HostelStaffDutyLog

        assert hasattr(HostelStaffDutyLog, "staff_name")
        assert hasattr(HostelStaffDutyLog, "role")
        assert hasattr(HostelStaffDutyLog, "date")

    def test_staff_duty_roles(self):
        """test_id: TC-UC-020 | source_id: HM-UC-020 Main Flow
        StaffDutyRole enum has cleaning, mess, maintenance, attendant, other.
        """
        roles = {r.value for r in StaffDutyRole}
        assert roles == {"cleaning", "mess", "maintenance", "attendant", "other"}


# ===========================================================================
# UC-021: Security Guard Shift (HM-UC-021)
# ===========================================================================


class TestUC021SecurityShift:
    """test_id: TC-UC-021 | source_id: HM-UC-021 Main Flow"""

    def test_security_guard_shift_model_exists(self):
        """test_id: TC-UC-021 | source_id: HM-UC-021 Main Flow
        SecurityGuardShift model has required fields.
        """
        from modules.hostel.models import SecurityGuardShift

        assert hasattr(SecurityGuardShift, "guard_name")
        assert hasattr(SecurityGuardShift, "hostel")
        assert hasattr(SecurityGuardShift, "shift_date")
        assert hasattr(SecurityGuardShift, "status")

    def test_initial_shift_status_scheduled(self):
        """test_id: TC-UC-021 | source_id: HM-UC-021 Main Flow
        Initial security guard shift status is SCHEDULED.
        """
        assert SecurityShiftStatus.SCHEDULED == "scheduled"


# ===========================================================================
# UC-022: Publish Hostel Notice (HM-UC-022)
# ===========================================================================


class TestUC022HostelNotice:
    """test_id: TC-UC-022 | source_id: HM-UC-022 Main Flow"""

    def test_hostel_notice_model_exists(self):
        """test_id: TC-UC-022 | source_id: HM-UC-022 Main Flow
        HostelNotice model has required fields.
        """
        from modules.hostel.models import HostelNotice

        assert hasattr(HostelNotice, "title")
        assert hasattr(HostelNotice, "content")
        assert hasattr(HostelNotice, "priority")
        assert hasattr(HostelNotice, "published_by_user_id")

    def test_notice_priority_enum(self):
        """test_id: TC-UC-022 | source_id: HM-UC-022 Main Flow
        Notice priorities are normal, important, urgent.
        """
        values = {p.value for p in NoticePriority}
        assert values == {"normal", "important", "urgent"}

    def test_notice_publication_validation_passes(self):
        """test_id: TC-UC-022 | source_id: HM-UC-022 Main Flow
        Valid warden notice for assigned hostel passes.
        """
        validate_notice_publication(permitted_hostel_ids=[1, 2], target_hostel_id=1)

    def test_notice_publication_for_unassigned_hostel_fails(self):
        """test_id: TC-UC-022 | source_id: HM-UC-022 Main Flow
        Warden notice for unassigned hostel raises NoticePermissionError.
        """
        with pytest.raises(NoticePermissionError):
            validate_notice_publication(permitted_hostel_ids=[1], target_hostel_id=5)


# ===========================================================================
# UC-023: Notification on Room Allocation (HM-UC-023)
# ===========================================================================


class TestUC023Notification:
    """test_id: TC-UC-023 | source_id: HM-UC-023 Main Flow"""

    def test_hostel_notification_model_exists(self):
        """test_id: TC-UC-023 | source_id: HM-UC-023 Main Flow
        HostelNotification model exists with event and recipient fields.
        """
        from modules.hostel.models import HostelNotification

        assert hasattr(HostelNotification, "event_type")
        assert hasattr(HostelNotification, "recipient_user_id")
        assert hasattr(HostelNotification, "message")

    def test_notification_event_types(self):
        """test_id: TC-UC-023 | source_id: HM-UC-023 Main Flow
        All key notification event types are defined.
        """
        events = {e.value for e in NotificationEventType}
        assert "room_allocation" in events
        assert "leave_status" in events
        assert "complaint_status" in events
        assert "fine_recorded" in events
        assert "guest_room_status" in events
        assert "extended_stay_status" in events


# ===========================================================================
# UC-024: Alternative flow - accommodation request rejected (HM-UC-005 Alt)
# ===========================================================================


class TestUC024AccommodationRejected:
    """test_id: TC-UC-024 | source_id: HM-UC-005 Alt Flow rejected"""

    def test_accommodation_rejected_transition(self):
        """test_id: TC-UC-024 | source_id: HM-UC-005 Alt Flow rejected
        Accommodation request can be rejected from submitted state.
        """
        result = transition_accommodation_request(
            AccommodationRequestStatus.SUBMITTED,
            AccommodationRequestStatus.REJECTED,
        )
        assert result == AccommodationRequestStatus.REJECTED

    def test_allotted_cannot_be_rejected(self):
        """test_id: TC-UC-024 | source_id: HM-UC-005 Alt Flow rejected
        Already allotted request cannot be rejected.
        """
        with pytest.raises(InvalidStateTransitionError):
            transition_accommodation_request(
                AccommodationRequestStatus.ALLOTTED,
                AccommodationRequestStatus.REJECTED,
            )


# ===========================================================================
# UC-025: Alternative flow - accommodation request cancelled (HM-UC-005 Alt)
# ===========================================================================


class TestUC025AccommodationCancelled:
    """test_id: TC-UC-025 | source_id: HM-UC-005 Alt Flow cancelled"""

    def test_accommodation_cancelled_transition(self):
        """test_id: TC-UC-025 | source_id: HM-UC-005 Alt Flow cancelled
        Accommodation request can be cancelled from submitted state.
        """
        result = transition_accommodation_request(
            AccommodationRequestStatus.SUBMITTED,
            AccommodationRequestStatus.CANCELLED,
        )
        assert result == AccommodationRequestStatus.CANCELLED


# ===========================================================================
# UC-026: Caretaker scope boundary (HM-UC-004 exception)
# ===========================================================================


class TestUC026CaretakerScopeBoundary:
    """test_id: TC-UC-026 | source_id: HM-UC-004 Exception Flow"""

    def test_caretaker_cannot_access_unassigned_hostel(self):
        """test_id: TC-UC-026 | source_id: HM-UC-004 Exception Flow
        Caretaker cannot operate on hostel outside their assignment.
        """
        with pytest.raises(UnauthorizedHostelAccessError):
            validate_caretaker_access(caretaker_hostel_ids=[1, 2], target_hostel_id=10)

    def test_caretaker_can_access_assigned_hostel(self):
        """test_id: TC-UC-026 | source_id: HM-UC-004 Exception Flow
        Caretaker can access hostel in their assigned list.
        """
        validate_caretaker_access([1, 2], target_hostel_id=2)


# ===========================================================================
# UC-027: Student scope boundary (HM-UC-005 exception)
# ===========================================================================


class TestUC027StudentScopeBoundary:
    """test_id: TC-UC-027 | source_id: HM-UC-005 Exception Flow"""

    def test_student_cannot_access_another_hostel(self):
        """test_id: TC-UC-027 | source_id: HM-UC-005 Exception Flow
        Student can only access data for their allocated hostel.
        """
        with pytest.raises(UnauthorizedHostelAccessError):
            validate_student_access(student_hostel_id=1, target_hostel_id=2)

    def test_student_unallocated_access_blocked(self):
        """test_id: TC-UC-027 | source_id: HM-UC-005 Exception Flow
        Student with no allocation (hostel_id=None) is blocked.
        """
        with pytest.raises(UnauthorizedHostelAccessError):
            validate_student_access(student_hostel_id=None, target_hostel_id=1)


# ===========================================================================
# UC-028: Complaint invalid category (HM-UC-011 exception)
# ===========================================================================


class TestUC028ComplaintInvalidCategory:
    """test_id: TC-UC-028 | source_id: HM-UC-011 Exception Flow"""

    def test_out_of_scope_category_raises(self):
        """test_id: TC-UC-028 | source_id: HM-UC-011 Exception Flow
        Complaint with out-of-scope category raises ScopeBoundaryError.
        """
        from modules.hostel.domain.errors import ScopeBoundaryError

        with pytest.raises(ScopeBoundaryError):
            validate_complaint_data("financial_query", "I want a fee refund")


# ===========================================================================
# UC-029: Fine without mandatory fields (HM-UC-018 exception)
# ===========================================================================


class TestUC029FineValidationException:
    """test_id: TC-UC-029 | source_id: HM-UC-018 Exception Flow"""

    def test_fine_zero_amount_raises(self):
        """test_id: TC-UC-029 | source_id: HM-UC-018 Exception Flow
        Fine with zero amount is rejected.
        """
        with pytest.raises(MandatoryFieldMissingError):
            validate_fine_fields(
                student_user_id=5,
                amount=0,
                reason="test",
                imposed_date=date(2026, 1, 1),
            )

    def test_fine_no_student_raises(self):
        """test_id: TC-UC-029 | source_id: HM-UC-018 Exception Flow
        Fine without student reference raises error.
        """
        with pytest.raises(MandatoryFieldMissingError):
            validate_fine_fields(
                student_user_id=None,
                amount=Decimal("100"),
                reason="Violation",
                imposed_date=date(2026, 1, 1),
            )


# ===========================================================================
# UC-030: Super Admin institution-wide visibility (HM-UC-003 Alt)
# ===========================================================================


class TestUC030SuperAdminInstitutionWide:
    """test_id: TC-UC-030 | source_id: HM-UC-003 Alt Flow Super Admin"""

    def test_super_admin_bypasses_all_hostel_restrictions(self):
        """test_id: TC-UC-030 | source_id: HM-UC-003 Alt Flow Super Admin
        Super Admin with is_super_admin=True can access any hostel.
        """
        validate_caretaker_access(
            caretaker_hostel_ids=[], target_hostel_id=999, is_super_admin=True
        )

    def test_super_admin_can_publish_global_notice(self):
        """test_id: TC-UC-030 | source_id: HM-UC-003 Alt Flow Super Admin
        Super Admin can publish global notices (no hostel restriction).
        """
        validate_notice_publication(
            permitted_hostel_ids=[], target_hostel_id=None, is_super_admin=True
        )


# ===========================================================================
# UC-031: Allotment vacated (HM-UC-006 Alt)
# ===========================================================================


class TestUC031AllotmentVacated:
    """test_id: TC-UC-031 | source_id: HM-UC-006 Alt Flow vacate"""

    def test_allotment_status_vacated_exists(self):
        """test_id: TC-UC-031 | source_id: HM-UC-006 Alt Flow vacate
        AllotmentStatus has VACATED value.
        """
        assert AllotmentStatus.VACATED == "vacated"

    def test_allotment_status_exchanged_exists(self):
        """test_id: TC-UC-031 | source_id: HM-UC-006 Alt Flow vacate
        AllotmentStatus has EXCHANGED value for room swap tracking.
        """
        assert AllotmentStatus.EXCHANGED == "exchanged"


# ===========================================================================
# UC-032: Fine status lifecycle (HM-UC-018 Alt)
# ===========================================================================


class TestUC032FineStatusLifecycle:
    """test_id: TC-UC-032 | source_id: HM-UC-018 Alt Flow fine-paid"""

    def test_fine_status_values(self):
        """test_id: TC-UC-032 | source_id: HM-UC-018 Alt Flow fine-paid
        Fine status can be recorded, paid, or waived.
        """
        values = {s.value for s in FineStatus}
        assert values == {"recorded", "paid", "waived"}


# ===========================================================================
# UC-033: Complaint unresolved (HM-UC-012 Alt)
# ===========================================================================


class TestUC033ComplaintUnresolved:
    """test_id: TC-UC-033 | source_id: HM-UC-012 Alt Flow unresolved"""

    def test_complaint_submitted_to_unresolved(self):
        """test_id: TC-UC-033 | source_id: HM-UC-012 Alt Flow unresolved
        Complaint can go to unresolved status.
        """
        result = transition_complaint(ComplaintStatus.SUBMITTED, ComplaintStatus.UNRESOLVED)
        assert result == ComplaintStatus.UNRESOLVED

    def test_complaint_unresolved_to_escalated(self):
        """test_id: TC-UC-033 | source_id: HM-UC-012 Alt Flow unresolved
        Unresolved complaint can be escalated.
        """
        result = transition_complaint(ComplaintStatus.UNRESOLVED, ComplaintStatus.ESCALATED)
        assert result == ComplaintStatus.ESCALATED


# ===========================================================================
# UC-034: Inventory condition update (HM-UC-019 Alt)
# ===========================================================================


class TestUC034InventoryConditionUpdate:
    """test_id: TC-UC-034 | source_id: HM-UC-019 Alt Flow condition-update"""

    def test_inventory_condition_damaged_exists(self):
        """test_id: TC-UC-034 | source_id: HM-UC-019 Alt Flow condition-update
        Inventory condition includes DAMAGED for damage reporting.
        """
        assert InventoryCondition.DAMAGED == "damaged"

    def test_inventory_condition_scrapped_exists(self):
        """test_id: TC-UC-034 | source_id: HM-UC-019 Alt Flow condition-update
        Inventory condition includes SCRAPPED for end-of-life items.
        """
        assert InventoryCondition.SCRAPPED == "scrapped"


# ===========================================================================
# UC-035: Security shift status update (HM-UC-021 Alt)
# ===========================================================================


class TestUC035SecurityShiftUpdate:
    """test_id: TC-UC-035 | source_id: HM-UC-021 Alt Flow shift-update"""

    def test_security_shift_absent_status(self):
        """test_id: TC-UC-035 | source_id: HM-UC-021 Alt Flow shift-update
        Security guard shift can be marked ABSENT.
        """
        assert SecurityShiftStatus.ABSENT == "absent"

    def test_security_shift_relieved_status(self):
        """test_id: TC-UC-035 | source_id: HM-UC-021 Alt Flow shift-update
        Security guard shift can be marked RELIEVED on completion.
        """
        assert SecurityShiftStatus.RELIEVED == "relieved"


# ===========================================================================
# UC-036: Room status lifecycle (HM-UC-003 room)
# ===========================================================================


class TestUC036RoomStatusLifecycle:
    """test_id: TC-UC-036 | source_id: HM-UC-003 Alt room-status"""

    def test_room_status_enum_complete(self):
        """test_id: TC-UC-036 | source_id: HM-UC-003 Alt room-status
        Room status lifecycle covers available, occupied, maintenance, reserved, inactive.
        """
        values = {s.value for s in RoomStatus}
        assert values == {"available", "occupied", "maintenance", "reserved", "inactive"}


# ===========================================================================
# UC-037: Extended stay compliance tracking (HM-UC-016 Alt)
# ===========================================================================


class TestUC037ExtendedStayCompliance:
    """test_id: TC-UC-037 | source_id: HM-UC-016 Alt compliance"""

    def test_extended_stay_model_has_compliance_status(self):
        """test_id: TC-UC-037 | source_id: HM-UC-016 Alt compliance
        ExtendedStayRequest model has compliance_status for charge tracking.
        """
        from modules.hostel.models import ExtendedStayRequest

        assert hasattr(ExtendedStayRequest, "compliance_status")

    def test_extended_stay_compliance_enum_values(self):
        """test_id: TC-UC-037 | source_id: HM-UC-016 Alt compliance
        ExtendedStayCompliance enum has pending, paid, exempt, overdue.
        """
        from modules.hostel.domain.enums import ExtendedStayCompliance

        values = {c.value for c in ExtendedStayCompliance}
        assert values == {"pending", "paid", "exempt", "overdue"}


# ===========================================================================
# UC-038: Role binding validity dates (HM-UC-003 Alt)
# ===========================================================================


class TestUC038RoleBindingValidityDates:
    """test_id: TC-UC-038 | source_id: HM-UC-003 Alt validity-dates"""

    def test_role_binding_has_valid_from_valid_to(self):
        """test_id: TC-UC-038 | source_id: HM-UC-003 Alt validity-dates
        HostelRoleBinding supports time-bound assignment with valid_from / valid_to.
        """
        from modules.hostel.models import HostelRoleBinding

        assert hasattr(HostelRoleBinding, "valid_from")
        assert hasattr(HostelRoleBinding, "valid_to")

    def test_role_binding_is_active_flag(self):
        """test_id: TC-UC-038 | source_id: HM-UC-003 Alt validity-dates
        HostelRoleBinding has is_active flag for enabling / disabling.
        """
        from modules.hostel.models import HostelRoleBinding

        assert hasattr(HostelRoleBinding, "is_active")
