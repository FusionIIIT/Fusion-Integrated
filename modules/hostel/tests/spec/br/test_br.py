"""Hostel Management - Business Rules Spec Tests (Prompt B).

Each test maps directly to a BR-HM-XXX entry in BR_DESIGN.json.
test_id and source_id are recorded in each test docstring.
"""

from datetime import date
from decimal import Decimal

import pytest

from modules.hostel.domain.enums import (
    AccommodationRequestStatus,
    ComplaintStatus,
    ExtendedStayStatus,
    GuestRoomBookingStatus,
    LeaveStatus,
    RoleBindingType,
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

# ---------------------------------------------------------------------------
# TC-BR-001: Super Admin binds Warden role (BR-HM-001 positive)
# ---------------------------------------------------------------------------


class TestBR001WardenRoleBinding:
    """test_id: TC-BR-001-P | source_id: BR-HM-001 condition-true"""

    def test_warden_role_binding_type_enum(self):
        """test_id: TC-BR-001-P | source_id: BR-HM-001 condition-true
        RoleBindingType WARDEN value is correctly defined.
        """
        assert RoleBindingType.WARDEN == "warden"

    def test_caretaker_role_binding_type_enum(self):
        """test_id: TC-BR-001-P | source_id: BR-HM-001 condition-true
        RoleBindingType CARETAKER value is correctly defined.
        """
        assert RoleBindingType.CARETAKER == "caretaker"


# ---------------------------------------------------------------------------
# TC-BR-002: Student cannot access outside allocated hostel (BR-HM-002 negative)
# ---------------------------------------------------------------------------


class TestBR002StudentScopeBoundary:
    """test_id: TC-BR-002-N | source_id: BR-HM-002 condition-false"""

    def test_student_cannot_access_different_hostel(self):
        """test_id: TC-BR-002-N | source_id: BR-HM-002 condition-false
        Student allocated to Hostel 1 cannot access Hostel 2.
        """
        with pytest.raises(UnauthorizedHostelAccessError):
            validate_student_access(student_hostel_id=1, target_hostel_id=2)

    def test_student_can_access_own_hostel(self):
        """test_id: TC-BR-002-N | source_id: BR-HM-002 condition-false
        Student allocated to Hostel 1 can access Hostel 1.
        """
        validate_student_access(student_hostel_id=1, target_hostel_id=1)


# ---------------------------------------------------------------------------
# TC-BR-003: Super Admin institution-wide access (BR-HM-003 positive)
# ---------------------------------------------------------------------------


class TestBR003SuperAdminAccess:
    """test_id: TC-BR-003-P | source_id: BR-HM-003 condition-true"""

    def test_super_admin_bypasses_caretaker_restriction(self):
        """test_id: TC-BR-003-P | source_id: BR-HM-003 condition-true
        Super Admin can access any hostel regardless of assignment.
        """
        validate_caretaker_access(
            caretaker_hostel_ids=[], target_hostel_id=999, is_super_admin=True
        )

    def test_super_admin_bypasses_notice_restriction(self):
        """test_id: TC-BR-003-P | source_id: BR-HM-003 condition-true
        Super Admin can publish global notices with no hostel restriction.
        """
        validate_notice_publication(
            permitted_hostel_ids=[], target_hostel_id=None, is_super_admin=True
        )


# ---------------------------------------------------------------------------
# TC-BR-004: Role binding time-bound validity (BR-HM-004 positive)
# ---------------------------------------------------------------------------


class TestBR004RoleBindingValidity:
    """test_id: TC-BR-004-P | source_id: BR-HM-004 condition-true"""

    def test_role_binding_dates_accepted(self):
        """test_id: TC-BR-004-P | source_id: BR-HM-004 condition-true
        Role binding model supports valid_from and valid_to dates.
        """
        from modules.hostel.models import HostelRoleBinding

        assert hasattr(HostelRoleBinding, "valid_from")
        assert hasattr(HostelRoleBinding, "valid_to")


# ---------------------------------------------------------------------------
# TC-BR-005: Unauthorized user refused (BR-HM-005 authorization)
# ---------------------------------------------------------------------------


class TestBR005UnauthorizedRefusal:
    """test_id: TC-BR-005-N | source_id: BR-HM-005 condition-false"""

    def test_caretaker_cannot_access_unassigned_hostel(self):
        """test_id: TC-BR-005-N | source_id: BR-HM-005 condition-false
        Caretaker without assignment to hostel is blocked.
        """
        with pytest.raises(UnauthorizedHostelAccessError):
            validate_caretaker_access(caretaker_hostel_ids=[1, 2], target_hostel_id=5)


# ---------------------------------------------------------------------------
# TC-BR-006: Newly assigned role holder sees pending records (BR-HM-006 positive)
# ---------------------------------------------------------------------------


class TestBR006ReassignedRoleAccess:
    """test_id: TC-BR-006-P | source_id: BR-HM-006 condition-true"""

    def test_newly_assigned_caretaker_can_access_hostel(self):
        """test_id: TC-BR-006-P | source_id: BR-HM-006 condition-true
        Caretaker just assigned to hostel 3 can access it.
        """
        validate_caretaker_access([3], target_hostel_id=3)


# ---------------------------------------------------------------------------
# TC-BR-007: Room capacity enforced (BR-HM-010)
# ---------------------------------------------------------------------------


class TestBR007RoomCapacityEnforced:
    """test_id: TC-BR-007-P | source_id: BR-HM-010 condition-true"""

    def test_capacity_exactly_at_limit_raises(self):
        """test_id: TC-BR-007-P | source_id: BR-HM-010 condition-true
        Adding one to a full room raises CapacityExceededError.
        """
        with pytest.raises(CapacityExceededError):
            validate_room_capacity(current_occupancy=4, room_capacity=4, adding=1)

    def test_capacity_below_limit_passes(self):
        """test_id: TC-BR-007-P | source_id: BR-HM-010 condition-true
        Adding one when below capacity passes.
        """
        validate_room_capacity(current_occupancy=3, room_capacity=4, adding=1)

    def test_capacity_multiple_students_raises(self):
        """test_id: TC-BR-007-P | source_id: BR-HM-010 condition-true
        Adding more than remaining capacity raises CapacityExceededError.
        """
        with pytest.raises(CapacityExceededError):
            validate_room_capacity(current_occupancy=3, room_capacity=4, adding=2)


# ---------------------------------------------------------------------------
# TC-BR-008: Mandatory fine fields (BR-HM-025)
# ---------------------------------------------------------------------------


class TestBR008FineFieldsMandatory:
    """test_id: TC-BR-008-P | source_id: BR-HM-025 condition-true"""

    def test_valid_fine_fields_pass(self):
        """test_id: TC-BR-008-P | source_id: BR-HM-025 condition-true
        Valid fine data passes all mandatory field checks.
        """
        validate_fine_fields(
            student_user_id=10,
            amount=Decimal("250.00"),
            reason="Late return from leave",
            imposed_date=date(2026, 3, 1),
        )

    def test_missing_reason_raises(self):
        """test_id: TC-BR-008-P | source_id: BR-HM-025 condition-true
        Fine without reason raises MandatoryFieldMissingError.
        """
        with pytest.raises(MandatoryFieldMissingError):
            validate_fine_fields(
                student_user_id=10,
                amount=Decimal("100"),
                reason="",
                imposed_date=date(2026, 3, 1),
            )

    def test_missing_date_raises(self):
        """test_id: TC-BR-008-P | source_id: BR-HM-025 condition-true
        Fine without imposed_date raises MandatoryFieldMissingError.
        """
        with pytest.raises(MandatoryFieldMissingError):
            validate_fine_fields(
                student_user_id=10,
                amount=Decimal("100"),
                reason="Violation",
                imposed_date=None,
            )


# ---------------------------------------------------------------------------
# TC-BR-009: Mandatory complaint fields (BR-HM-015)
# ---------------------------------------------------------------------------


class TestBR009ComplaintFieldsMandatory:
    """test_id: TC-BR-009-P | source_id: BR-HM-015 condition-true"""

    def test_valid_complaint_passes(self):
        """test_id: TC-BR-009-P | source_id: BR-HM-015 condition-true
        Valid category and description passes complaint validation.
        """
        validate_complaint_data("electrical", "Fan is not working")

    def test_empty_description_raises(self):
        """test_id: TC-BR-009-P | source_id: BR-HM-015 condition-true
        Empty description raises MandatoryFieldMissingError.
        """
        with pytest.raises(MandatoryFieldMissingError):
            validate_complaint_data("electrical", "")

    def test_none_description_raises(self):
        """test_id: TC-BR-009-P | source_id: BR-HM-015 condition-true
        None description raises MandatoryFieldMissingError.
        """
        with pytest.raises(MandatoryFieldMissingError):
            validate_complaint_data("electrical", None)


# ---------------------------------------------------------------------------
# TC-BR-010: Complaint scope boundary (BR-HM-016)
# ---------------------------------------------------------------------------


class TestBR010ComplaintScope:
    """test_id: TC-BR-010-N | source_id: BR-HM-016 condition-false"""

    def test_invalid_complaint_category_raises(self):
        """test_id: TC-BR-010-N | source_id: BR-HM-016 condition-false
        Out-of-scope complaint category raises ScopeBoundaryError.
        """
        with pytest.raises(ScopeBoundaryError):
            validate_complaint_data("financial_dispute", "I want refund")

    def test_valid_categories_all_pass(self):
        """test_id: TC-BR-010-N | source_id: BR-HM-016 condition-false
        All valid complaint categories pass.
        """
        from modules.hostel.domain.enums import ComplaintCategory

        for cat in ComplaintCategory:
            validate_complaint_data(cat.value, "Some description about the issue")


# ---------------------------------------------------------------------------
# TC-BR-011: Notice scope BR-HM-029
# ---------------------------------------------------------------------------


class TestBR011NoticeScope:
    """test_id: TC-BR-011-P | source_id: BR-HM-029 condition-true"""

    def test_warden_cannot_publish_for_unassigned_hostel(self):
        """test_id: TC-BR-011-P | source_id: BR-HM-029 condition-true
        Warden publishing for unassigned hostel raises NoticePermissionError.
        """
        with pytest.raises(NoticePermissionError):
            validate_notice_publication(permitted_hostel_ids=[1, 2], target_hostel_id=5)

    def test_warden_can_publish_for_assigned_hostel(self):
        """test_id: TC-BR-011-P | source_id: BR-HM-029 condition-true
        Warden publishing for assigned hostel passes.
        """
        validate_notice_publication(permitted_hostel_ids=[1, 2], target_hostel_id=2)


# ---------------------------------------------------------------------------
# TC-BR-012: Caretaker scope boundary (BR-HM-035)
# ---------------------------------------------------------------------------


class TestBR012CaretakerScope:
    """test_id: TC-BR-012-N | source_id: BR-HM-035 condition-false"""

    def test_caretaker_outside_scope_blocked(self):
        """test_id: TC-BR-012-N | source_id: BR-HM-035 condition-false
        Caretaker operating outside their hostel scope is blocked.
        """
        with pytest.raises(UnauthorizedHostelAccessError):
            validate_caretaker_access(caretaker_hostel_ids=[10, 11], target_hostel_id=20)

    def test_caretaker_within_scope_allowed(self):
        """test_id: TC-BR-012-N | source_id: BR-HM-035 condition-false
        Caretaker within their hostel scope is allowed.
        """
        validate_caretaker_access([10, 11], target_hostel_id=10)


# ---------------------------------------------------------------------------
# TC-BR-013..026: State machine guard rules
# ---------------------------------------------------------------------------


class TestBR013AccommodationTransitions:
    """test_id: TC-BR-013-P | source_id: BR-HM-010 state-guard"""

    def test_submitted_to_allotted(self):
        """test_id: TC-BR-013-P | source_id: BR-HM-010 state-guard
        Accommodation request: submitted -> allotted transition valid.
        """
        result = transition_accommodation_request(
            AccommodationRequestStatus.SUBMITTED, AccommodationRequestStatus.ALLOTTED
        )
        assert result == AccommodationRequestStatus.ALLOTTED

    def test_submitted_to_rejected(self):
        """test_id: TC-BR-013-P | source_id: BR-HM-010 state-guard
        Accommodation request: submitted -> rejected transition valid.
        """
        result = transition_accommodation_request(
            AccommodationRequestStatus.SUBMITTED, AccommodationRequestStatus.REJECTED
        )
        assert result == AccommodationRequestStatus.REJECTED

    def test_submitted_to_cancelled(self):
        """test_id: TC-BR-013-P | source_id: BR-HM-010 state-guard
        Accommodation request: submitted -> cancelled transition valid.
        """
        result = transition_accommodation_request(
            AccommodationRequestStatus.SUBMITTED, AccommodationRequestStatus.CANCELLED
        )
        assert result == AccommodationRequestStatus.CANCELLED

    def test_allotted_to_allotted_invalid(self):
        """test_id: TC-BR-013-P | source_id: BR-HM-010 state-guard
        Accommodation request: allotted -> allotted is invalid.
        """
        with pytest.raises(InvalidStateTransitionError):
            transition_accommodation_request(
                AccommodationRequestStatus.ALLOTTED, AccommodationRequestStatus.ALLOTTED
            )


class TestBR014LeaveTransitions:
    """test_id: TC-BR-014-P | source_id: BR-HM-002 state-guard"""

    def test_submitted_to_approved(self):
        """test_id: TC-BR-014-P | source_id: BR-HM-002 state-guard
        Leave: submitted -> approved transition valid.
        """
        result = transition_leave_request(LeaveStatus.SUBMITTED, LeaveStatus.APPROVED)
        assert result == LeaveStatus.APPROVED

    def test_submitted_to_rejected(self):
        """test_id: TC-BR-014-P | source_id: BR-HM-002 state-guard
        Leave: submitted -> rejected transition valid.
        """
        result = transition_leave_request(LeaveStatus.SUBMITTED, LeaveStatus.REJECTED)
        assert result == LeaveStatus.REJECTED

    def test_approved_to_rejected_invalid(self):
        """test_id: TC-BR-014-P | source_id: BR-HM-002 state-guard
        Leave: approved -> rejected is invalid.
        """
        with pytest.raises(InvalidStateTransitionError):
            transition_leave_request(LeaveStatus.APPROVED, LeaveStatus.REJECTED)

    def test_rejected_to_approved_invalid(self):
        """test_id: TC-BR-014-P | source_id: BR-HM-002 state-guard
        Leave: rejected -> approved is invalid.
        """
        with pytest.raises(InvalidStateTransitionError):
            transition_leave_request(LeaveStatus.REJECTED, LeaveStatus.APPROVED)


class TestBR015ComplaintTransitions:
    """test_id: TC-BR-015-P | source_id: BR-HM-015 state-guard"""

    def test_submitted_to_unresolved(self):
        """test_id: TC-BR-015-P | source_id: BR-HM-015 state-guard
        Complaint: submitted -> unresolved valid.
        """
        result = transition_complaint(ComplaintStatus.SUBMITTED, ComplaintStatus.UNRESOLVED)
        assert result == ComplaintStatus.UNRESOLVED

    def test_unresolved_to_resolved(self):
        """test_id: TC-BR-015-P | source_id: BR-HM-015 state-guard
        Complaint: unresolved -> resolved valid.
        """
        result = transition_complaint(ComplaintStatus.UNRESOLVED, ComplaintStatus.RESOLVED)
        assert result == ComplaintStatus.RESOLVED

    def test_resolved_to_escalated_invalid(self):
        """test_id: TC-BR-015-P | source_id: BR-HM-015 state-guard
        Complaint: resolved -> escalated is invalid.
        """
        with pytest.raises(InvalidStateTransitionError):
            transition_complaint(ComplaintStatus.RESOLVED, ComplaintStatus.ESCALATED)


class TestBR016GuestBookingTransitions:
    """test_id: TC-BR-016-P | source_id: BR-HM-003 state-guard"""

    def test_submitted_to_approved(self):
        """test_id: TC-BR-016-P | source_id: BR-HM-003 state-guard
        Guest booking: submitted -> approved valid.
        """
        result = transition_guest_room_booking(
            GuestRoomBookingStatus.SUBMITTED, GuestRoomBookingStatus.APPROVED
        )
        assert result == GuestRoomBookingStatus.APPROVED

    def test_submitted_to_rejected(self):
        """test_id: TC-BR-016-P | source_id: BR-HM-003 state-guard
        Guest booking: submitted -> rejected valid.
        """
        result = transition_guest_room_booking(
            GuestRoomBookingStatus.SUBMITTED, GuestRoomBookingStatus.REJECTED
        )
        assert result == GuestRoomBookingStatus.REJECTED

    def test_approved_to_rejected_invalid(self):
        """test_id: TC-BR-016-P | source_id: BR-HM-003 state-guard
        Guest booking: approved -> rejected is invalid.
        """
        with pytest.raises(InvalidStateTransitionError):
            transition_guest_room_booking(
                GuestRoomBookingStatus.APPROVED, GuestRoomBookingStatus.REJECTED
            )


class TestBR017ExtendedStayTransitions:
    """test_id: TC-BR-017-P | source_id: BR-HM-004 state-guard"""

    def test_submitted_to_approved(self):
        """test_id: TC-BR-017-P | source_id: BR-HM-004 state-guard
        Extended stay: submitted -> approved valid.
        """
        result = transition_extended_stay(ExtendedStayStatus.SUBMITTED, ExtendedStayStatus.APPROVED)
        assert result == ExtendedStayStatus.APPROVED

    def test_submitted_to_rejected(self):
        """test_id: TC-BR-017-P | source_id: BR-HM-004 state-guard
        Extended stay: submitted -> rejected valid.
        """
        result = transition_extended_stay(ExtendedStayStatus.SUBMITTED, ExtendedStayStatus.REJECTED)
        assert result == ExtendedStayStatus.REJECTED

    def test_rejected_to_approved_invalid(self):
        """test_id: TC-BR-017-P | source_id: BR-HM-004 state-guard
        Extended stay: rejected -> approved is invalid.
        """
        with pytest.raises(InvalidStateTransitionError):
            transition_extended_stay(ExtendedStayStatus.REJECTED, ExtendedStayStatus.APPROVED)
