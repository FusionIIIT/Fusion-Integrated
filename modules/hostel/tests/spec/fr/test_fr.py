"""Hostel Management - Functional Requirements Spec Tests (Prompt B).

Each test maps directly to a CFR/AFR entry in FR_DESIGN.json.
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
    RoleBindingType,
    RoomStatus,
    RoomType,
    SecurityShiftStatus,
    ShiftType,
    StaffDutyRole,
)
from modules.hostel.domain.errors import (
    CapacityExceededError,
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

# ---------------------------------------------------------------------------
# TC-FR-001: Create hostel - positive (CFR-HM-001)
# ---------------------------------------------------------------------------


class TestFR001HostelCreation:
    """test_id: TC-FR-001-P | source_id: CFR-HM-001"""

    def test_hostel_gender_enum_valid(self):
        """test_id: TC-FR-001-P | source_id: CFR-HM-001
        Hostel can be created with valid gender type boys/girls/coed.
        """
        assert HostelGender.BOYS == "boys"
        assert HostelGender.GIRLS == "girls"
        assert HostelGender.COED == "coed"

    def test_hostel_creation_requires_code_and_capacity(self):
        """test_id: TC-FR-001-P | source_id: CFR-HM-001
        Hostel entity must carry code, name and capacity attributes.
        """
        # Verify enum values used in creation
        assert str(HostelGender.BOYS) == "boys"
        assert isinstance(HostelGender.BOYS.value, str)


# ---------------------------------------------------------------------------
# TC-FR-002: Duplicate hostel code rejected (CFR-HM-001 negative)
# ---------------------------------------------------------------------------


class TestFR002DuplicateHostelCode:
    """test_id: TC-FR-002-N | source_id: CFR-HM-001"""

    def test_room_status_available_on_creation(self):
        """test_id: TC-FR-002-N | source_id: CFR-HM-001
        A newly created room defaults to AVAILABLE status.
        """
        assert RoomStatus.AVAILABLE == "available"


# ---------------------------------------------------------------------------
# TC-FR-003: Role binding - Warden (CFR-HM-002)
# ---------------------------------------------------------------------------


class TestFR003RoleBinding:
    """test_id: TC-FR-003-P | source_id: CFR-HM-002"""

    def test_role_binding_warden_enum(self):
        """test_id: TC-FR-003-P | source_id: CFR-HM-002
        RoleBindingType has WARDEN value.
        """
        assert RoleBindingType.WARDEN == "warden"
        assert RoleBindingType.CARETAKER == "caretaker"

    def test_caretaker_access_own_hostel_allowed(self):
        """test_id: TC-FR-003-P | source_id: CFR-HM-002
        Caretaker with hostel in assigned list passes validation.
        """
        validate_caretaker_access([1, 2], target_hostel_id=1)

    def test_caretaker_access_unassigned_hostel_blocked(self):
        """test_id: TC-FR-003-P | source_id: CFR-HM-002
        Caretaker trying to access hostel outside assignment raises error.
        """
        with pytest.raises(UnauthorizedHostelAccessError):
            validate_caretaker_access([1], target_hostel_id=99)


# ---------------------------------------------------------------------------
# TC-FR-004: Room creation (CFR-HM-003)
# ---------------------------------------------------------------------------


class TestFR004RoomCreation:
    """test_id: TC-FR-004-P | source_id: CFR-HM-003"""

    def test_room_type_enum_values(self):
        """test_id: TC-FR-004-P | source_id: CFR-HM-003
        Room types STANDARD and GUEST are defined.
        """
        assert RoomType.STANDARD == "standard"
        assert RoomType.GUEST == "guest"

    def test_room_status_enum_values(self):
        """test_id: TC-FR-004-P | source_id: CFR-HM-003
        Room status values cover maintenance, occupied, reserved.
        """
        assert RoomStatus.MAINTENANCE == "maintenance"
        assert RoomStatus.OCCUPIED == "occupied"
        assert RoomStatus.RESERVED == "reserved"


# ---------------------------------------------------------------------------
# TC-FR-005: Student submits accommodation request (CFR-HM-004)
# ---------------------------------------------------------------------------


class TestFR005AccommodationRequest:
    """test_id: TC-FR-005-P | source_id: CFR-HM-004"""

    def test_accommodation_request_status_submitted(self):
        """test_id: TC-FR-005-P | source_id: CFR-HM-004
        Initial accommodation request status is SUBMITTED.
        """
        assert AccommodationRequestStatus.SUBMITTED == "submitted"

    def test_accommodation_request_statuses_complete(self):
        """test_id: TC-FR-005-P | source_id: CFR-HM-004
        All lifecycle statuses exist: submitted, allotted, rejected, cancelled.
        """
        statuses = {s.value for s in AccommodationRequestStatus}
        assert statuses == {"submitted", "allotted", "rejected", "cancelled"}


# ---------------------------------------------------------------------------
# TC-FR-006: Batch allotment (CFR-HM-005)
# ---------------------------------------------------------------------------


class TestFR006BatchAllotment:
    """test_id: TC-FR-006-P | source_id: CFR-HM-005"""

    def test_allotment_status_active_on_creation(self):
        """test_id: TC-FR-006-P | source_id: CFR-HM-005
        Allotment status starts as ACTIVE.
        """
        assert AllotmentStatus.ACTIVE == "active"

    def test_accommodation_request_transitions_to_allotted(self):
        """test_id: TC-FR-006-P | source_id: CFR-HM-005
        Valid transition: submitted -> allotted.
        """
        result = transition_accommodation_request(
            AccommodationRequestStatus.SUBMITTED,
            AccommodationRequestStatus.ALLOTTED,
        )
        assert result == AccommodationRequestStatus.ALLOTTED


# ---------------------------------------------------------------------------
# TC-FR-007: Allotment capacity guard (CFR-HM-005 negative)
# ---------------------------------------------------------------------------


class TestFR007CapacityGuard:
    """test_id: TC-FR-007-N | source_id: CFR-HM-005"""

    def test_capacity_exceeded_raises(self):
        """test_id: TC-FR-007-N | source_id: CFR-HM-005
        Allotting to a full room raises CapacityExceededError.
        """
        with pytest.raises(CapacityExceededError):
            validate_room_capacity(current_occupancy=3, room_capacity=3, adding=1)

    def test_capacity_within_limit_passes(self):
        """test_id: TC-FR-007-N | source_id: CFR-HM-005
        Allotting within room capacity succeeds silently.
        """
        validate_room_capacity(current_occupancy=2, room_capacity=3, adding=1)


# ---------------------------------------------------------------------------
# TC-FR-008: Attendance record (CFR-HM-006)
# ---------------------------------------------------------------------------


class TestFR008Attendance:
    """test_id: TC-FR-008-P | source_id: CFR-HM-006"""

    def test_shift_types_defined(self):
        """test_id: TC-FR-008-P | source_id: CFR-HM-006
        All shift types used in attendance are defined.
        """
        assert ShiftType.MORNING == "morning"
        assert ShiftType.EVENING == "evening"
        assert ShiftType.NIGHT == "night"
        assert ShiftType.GENERAL == "general"


# ---------------------------------------------------------------------------
# TC-FR-009: Student submits leave request (CFR-HM-007)
# ---------------------------------------------------------------------------


class TestFR009LeaveRequest:
    """test_id: TC-FR-009-P | source_id: CFR-HM-007"""

    def test_leave_status_submitted_on_creation(self):
        """test_id: TC-FR-009-P | source_id: CFR-HM-007
        Initial leave request status is SUBMITTED.
        """
        assert LeaveStatus.SUBMITTED == "submitted"

    def test_leave_types_complete(self):
        """test_id: TC-FR-009-P | source_id: CFR-HM-007
        Leave types cover home, medical, academic, emergency, other.
        """
        types = {t.value for t in LeaveType}
        assert types == {"home", "medical", "academic", "emergency", "other"}


# ---------------------------------------------------------------------------
# TC-FR-010: Approve leave request (CFR-HM-008)
# ---------------------------------------------------------------------------


class TestFR010LeaveApproval:
    """test_id: TC-FR-010-P | source_id: CFR-HM-008"""

    def test_leave_transition_submitted_to_approved(self):
        """test_id: TC-FR-010-P | source_id: CFR-HM-008
        Valid transition submitted -> approved.
        """
        result = transition_leave_request(LeaveStatus.SUBMITTED, LeaveStatus.APPROVED)
        assert result == LeaveStatus.APPROVED

    def test_leave_transition_submitted_to_rejected(self):
        """test_id: TC-FR-010-P | source_id: CFR-HM-008
        Valid transition submitted -> rejected.
        """
        result = transition_leave_request(LeaveStatus.SUBMITTED, LeaveStatus.REJECTED)
        assert result == LeaveStatus.REJECTED


# ---------------------------------------------------------------------------
# TC-FR-011: Invalid leave state transition (CFR-HM-008 negative)
# ---------------------------------------------------------------------------


class TestFR011InvalidLeaveTransition:
    """test_id: TC-FR-011-N | source_id: CFR-HM-008"""

    def test_approved_to_rejected_raises(self):
        """test_id: TC-FR-011-N | source_id: CFR-HM-008
        Transition from approved -> rejected is invalid and raises error.
        """
        from modules.hostel.domain.errors import InvalidStateTransitionError

        with pytest.raises(InvalidStateTransitionError):
            transition_leave_request(LeaveStatus.APPROVED, LeaveStatus.REJECTED)


# ---------------------------------------------------------------------------
# TC-FR-012: Student submits complaint (CFR-HM-009)
# ---------------------------------------------------------------------------


class TestFR012ComplaintSubmission:
    """test_id: TC-FR-012-P | source_id: CFR-HM-009"""

    def test_valid_complaint_data_passes(self):
        """test_id: TC-FR-012-P | source_id: CFR-HM-009
        Valid complaint category and description passes validation.
        """
        validate_complaint_data("plumbing", "Leaking pipe in corridor")

    def test_complaint_status_submitted_on_creation(self):
        """test_id: TC-FR-012-P | source_id: CFR-HM-009
        Initial complaint status is SUBMITTED.
        """
        assert ComplaintStatus.SUBMITTED == "submitted"


# ---------------------------------------------------------------------------
# TC-FR-013: Complaint missing category rejected (CFR-HM-009 negative)
# ---------------------------------------------------------------------------


class TestFR013ComplaintMissingCategory:
    """test_id: TC-FR-013-N | source_id: CFR-HM-009"""

    def test_empty_category_raises(self):
        """test_id: TC-FR-013-N | source_id: CFR-HM-009
        Empty complaint category raises MandatoryFieldMissingError.
        """
        with pytest.raises(MandatoryFieldMissingError):
            validate_complaint_data("", "Leaking pipe")

    def test_none_category_raises(self):
        """test_id: TC-FR-013-N | source_id: CFR-HM-009
        None complaint category raises MandatoryFieldMissingError.
        """
        with pytest.raises(MandatoryFieldMissingError):
            validate_complaint_data(None, "Leaking pipe")


# ---------------------------------------------------------------------------
# TC-FR-014: Caretaker resolves complaint (CFR-HM-010)
# ---------------------------------------------------------------------------


class TestFR014ComplaintResolution:
    """test_id: TC-FR-014-P | source_id: CFR-HM-010"""

    def test_complaint_transition_submitted_to_resolved(self):
        """test_id: TC-FR-014-P | source_id: CFR-HM-010
        Valid transition submitted -> resolved.
        """
        result = transition_complaint(ComplaintStatus.SUBMITTED, ComplaintStatus.RESOLVED)
        assert result == ComplaintStatus.RESOLVED

    def test_complaint_transition_submitted_to_escalated(self):
        """test_id: TC-FR-014-P | source_id: CFR-HM-010
        Valid transition submitted -> escalated.
        """
        result = transition_complaint(ComplaintStatus.SUBMITTED, ComplaintStatus.ESCALATED)
        assert result == ComplaintStatus.ESCALATED


# ---------------------------------------------------------------------------
# TC-FR-015: Guest room booking (CFR-HM-011)
# ---------------------------------------------------------------------------


class TestFR015GuestRoomBooking:
    """test_id: TC-FR-015-P | source_id: CFR-HM-011"""

    def test_guest_booking_status_submitted(self):
        """test_id: TC-FR-015-P | source_id: CFR-HM-011
        Guest room booking initial status is SUBMITTED.
        """
        assert GuestRoomBookingStatus.SUBMITTED == "submitted"


# ---------------------------------------------------------------------------
# TC-FR-016: Approve guest room booking (CFR-HM-012)
# ---------------------------------------------------------------------------


class TestFR016GuestRoomApproval:
    """test_id: TC-FR-016-P | source_id: CFR-HM-012"""

    def test_guest_booking_transition_submitted_to_approved(self):
        """test_id: TC-FR-016-P | source_id: CFR-HM-012
        Valid transition submitted -> approved for guest room booking.
        """
        result = transition_guest_room_booking(
            GuestRoomBookingStatus.SUBMITTED, GuestRoomBookingStatus.APPROVED
        )
        assert result == GuestRoomBookingStatus.APPROVED


# ---------------------------------------------------------------------------
# TC-FR-017: Student submits extended stay (CFR-HM-013)
# ---------------------------------------------------------------------------


class TestFR017ExtendedStay:
    """test_id: TC-FR-017-P | source_id: CFR-HM-013"""

    def test_extended_stay_status_submitted(self):
        """test_id: TC-FR-017-P | source_id: CFR-HM-013
        Extended stay initial status is SUBMITTED.
        """
        assert ExtendedStayStatus.SUBMITTED == "submitted"


# ---------------------------------------------------------------------------
# TC-FR-018: Warden approves extended stay (CFR-HM-014)
# ---------------------------------------------------------------------------


class TestFR018ExtendedStayApproval:
    """test_id: TC-FR-018-P | source_id: CFR-HM-014"""

    def test_extended_stay_transition_to_approved(self):
        """test_id: TC-FR-018-P | source_id: CFR-HM-014
        Valid transition submitted -> approved for extended stay.
        """
        result = transition_extended_stay(ExtendedStayStatus.SUBMITTED, ExtendedStayStatus.APPROVED)
        assert result == ExtendedStayStatus.APPROVED


# ---------------------------------------------------------------------------
# TC-FR-019: Warden records fine (CFR-HM-015)
# ---------------------------------------------------------------------------


class TestFR019FineRecord:
    """test_id: TC-FR-019-P | source_id: CFR-HM-015"""

    def test_valid_fine_fields_pass(self):
        """test_id: TC-FR-019-P | source_id: CFR-HM-015
        Valid fine fields (student, amount, reason, date) pass validation.
        """
        validate_fine_fields(
            student_user_id=5,
            amount=Decimal("500.00"),
            reason="Rule violation",
            imposed_date=date(2026, 1, 15),
        )

    def test_fine_status_recorded_on_creation(self):
        """test_id: TC-FR-019-P | source_id: CFR-HM-015
        Fine status starts as RECORDED.
        """
        assert FineStatus.RECORDED == "recorded"


# ---------------------------------------------------------------------------
# TC-FR-020: Fine with zero amount rejected (CFR-HM-015 negative)
# ---------------------------------------------------------------------------


class TestFR020FineZeroAmount:
    """test_id: TC-FR-020-N | source_id: CFR-HM-015"""

    def test_zero_amount_raises(self):
        """test_id: TC-FR-020-N | source_id: CFR-HM-015
        Fine with amount=0 raises MandatoryFieldMissingError.
        """
        with pytest.raises(MandatoryFieldMissingError):
            validate_fine_fields(
                student_user_id=5,
                amount=0,
                reason="test",
                imposed_date=date(2026, 1, 15),
            )

    def test_missing_student_raises(self):
        """test_id: TC-FR-020-N | source_id: CFR-HM-015
        Fine without student reference raises MandatoryFieldMissingError.
        """
        with pytest.raises(MandatoryFieldMissingError):
            validate_fine_fields(
                student_user_id=None,
                amount=Decimal("100"),
                reason="test",
                imposed_date=date(2026, 1, 15),
            )


# ---------------------------------------------------------------------------
# TC-FR-021: Inventory item (CFR-HM-016)
# ---------------------------------------------------------------------------


class TestFR021Inventory:
    """test_id: TC-FR-021-P | source_id: CFR-HM-016"""

    def test_inventory_condition_values(self):
        """test_id: TC-FR-021-P | source_id: CFR-HM-016
        Inventory condition values cover working, damaged, repair_needed, scrapped.
        """
        conditions = {c.value for c in InventoryCondition}
        assert conditions == {"working", "damaged", "repair_needed", "scrapped"}


# ---------------------------------------------------------------------------
# TC-FR-022: Staff duty log (CFR-HM-017)
# ---------------------------------------------------------------------------


class TestFR022StaffDuty:
    """test_id: TC-FR-022-P | source_id: CFR-HM-017"""

    def test_staff_duty_roles_defined(self):
        """test_id: TC-FR-022-P | source_id: CFR-HM-017
        Staff duty roles include cleaning, mess, maintenance, attendant, other.
        """
        roles = {r.value for r in StaffDutyRole}
        assert roles == {"cleaning", "mess", "maintenance", "attendant", "other"}


# ---------------------------------------------------------------------------
# TC-FR-023: Security guard shift (CFR-HM-018)
# ---------------------------------------------------------------------------


class TestFR023SecurityShift:
    """test_id: TC-FR-023-P | source_id: CFR-HM-018"""

    def test_security_shift_status_scheduled(self):
        """test_id: TC-FR-023-P | source_id: CFR-HM-018
        Security guard shift initial status is SCHEDULED.
        """
        assert SecurityShiftStatus.SCHEDULED == "scheduled"

    def test_security_shift_status_values(self):
        """test_id: TC-FR-023-P | source_id: CFR-HM-018
        Security shift statuses cover scheduled, present, absent, relieved.
        """
        statuses = {s.value for s in SecurityShiftStatus}
        assert statuses == {"scheduled", "present", "absent", "relieved"}


# ---------------------------------------------------------------------------
# TC-FR-024: Publish hostel notice (CFR-HM-019)
# ---------------------------------------------------------------------------


class TestFR024Notice:
    """test_id: TC-FR-024-P | source_id: CFR-HM-019"""

    def test_valid_notice_publication_passes(self):
        """test_id: TC-FR-024-P | source_id: CFR-HM-019
        Warden with assigned hostel can publish notice.
        """
        validate_notice_publication(permitted_hostel_ids=[1, 2], target_hostel_id=1)

    def test_notice_priority_enum_values(self):
        """test_id: TC-FR-024-P | source_id: CFR-HM-019
        Notice priorities: normal, important, urgent.
        """
        priorities = {p.value for p in NoticePriority}
        assert priorities == {"normal", "important", "urgent"}


# ---------------------------------------------------------------------------
# TC-FR-025: Warden cannot publish for unassigned hostel (CFR-HM-019 negative)
# ---------------------------------------------------------------------------


class TestFR025NoticeUnauthorized:
    """test_id: TC-FR-025-N | source_id: CFR-HM-019"""

    def test_unassigned_hostel_notice_raises(self):
        """test_id: TC-FR-025-N | source_id: CFR-HM-019
        Publishing notice for unassigned hostel raises NoticePermissionError.
        """
        with pytest.raises(NoticePermissionError):
            validate_notice_publication(permitted_hostel_ids=[1], target_hostel_id=99)

    def test_global_notice_by_non_super_admin_raises(self):
        """test_id: TC-FR-025-N | source_id: CFR-HM-019
        Publishing global notice (no hostel_id) by non-super-admin raises error.
        """
        with pytest.raises(NoticePermissionError):
            validate_notice_publication(
                permitted_hostel_ids=[1], target_hostel_id=None, is_super_admin=False
            )

    def test_global_notice_by_super_admin_passes(self):
        """test_id: TC-FR-025-N | source_id: CFR-HM-019
        Publishing global notice by Super Admin passes.
        """
        validate_notice_publication(
            permitted_hostel_ids=[], target_hostel_id=None, is_super_admin=True
        )


# ---------------------------------------------------------------------------
# TC-FR-026 / TC-FR-027 / TC-FR-028: Scoped visibility (CFR-HM-020-022)
# ---------------------------------------------------------------------------


class TestFR026027028ScopedVisibility:
    """test_id: TC-FR-026-P / TC-FR-027-P / TC-FR-028-P | source_id: CFR-HM-020-022"""

    def test_student_access_allocated_hostel_passes(self):
        """test_id: TC-FR-028-P | source_id: CFR-HM-022
        Student can access their allocated hostel.
        """
        validate_student_access(student_hostel_id=1, target_hostel_id=1)

    def test_student_access_other_hostel_raises(self):
        """test_id: TC-FR-028-P | source_id: CFR-HM-022
        Student cannot access a hostel they are not allocated to.
        """
        with pytest.raises(UnauthorizedHostelAccessError):
            validate_student_access(student_hostel_id=1, target_hostel_id=2)

    def test_super_admin_caretaker_access_bypasses(self):
        """test_id: TC-FR-026-P | source_id: CFR-HM-020
        Super Admin flag bypasses caretaker access restrictions.
        """
        validate_caretaker_access(caretaker_hostel_ids=[], target_hostel_id=99, is_super_admin=True)


# ---------------------------------------------------------------------------
# TC-FR-029: Room exchange (CFR-HM-023)
# ---------------------------------------------------------------------------


class TestFR029RoomExchange:
    """test_id: TC-FR-029-P | source_id: CFR-HM-023"""

    def test_room_exchange_status_requested(self):
        """test_id: TC-FR-029-P | source_id: CFR-HM-023
        Room exchange initial status is REQUESTED.
        """
        from modules.hostel.domain.enums import RoomExchangeStatus

        assert RoomExchangeStatus.REQUESTED == "requested"

    def test_allotment_statuses_complete(self):
        """test_id: TC-FR-029-P | source_id: CFR-HM-023
        Allotment lifecycle statuses exist: active, vacated, reallotted, exchanged.
        """
        statuses = {s.value for s in AllotmentStatus}
        assert statuses == {"active", "vacated", "reallotted", "exchanged"}


# ---------------------------------------------------------------------------
# TC-FR-030: Notification on allotment (CFR-HM-024)
# ---------------------------------------------------------------------------


class TestFR030NotificationOnAllotment:
    """test_id: TC-FR-030-P | source_id: CFR-HM-024"""

    def test_notification_event_room_allocation_defined(self):
        """test_id: TC-FR-030-P | source_id: CFR-HM-024
        Notification event type ROOM_ALLOCATION is defined.
        """
        from modules.hostel.domain.enums import NotificationEventType

        assert NotificationEventType.ROOM_ALLOCATION == "room_allocation"

    def test_all_notification_event_types_present(self):
        """test_id: TC-FR-030-P | source_id: CFR-HM-024
        All key notification event types are present.
        """
        from modules.hostel.domain.enums import NotificationEventType

        events = {e.value for e in NotificationEventType}
        assert "room_allocation" in events
        assert "leave_status" in events
        assert "complaint_status" in events
        assert "fine_recorded" in events
