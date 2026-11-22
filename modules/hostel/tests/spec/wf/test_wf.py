"""Hostel Management – Workflow State-Machine Spec Tests (Prompt B).

Each test maps directly to a BW-HM-XX / CW-HM-XX entry in WF_DESIGN.json.
test_id and source_id are recorded in each test docstring.
"""

import pytest

from modules.hostel.domain.enums import (
    AccommodationRequestStatus,
    AllotmentStatus,
    ComplaintStatus,
    ExtendedStayStatus,
    GuestRoomBookingStatus,
    LeaveStatus,
)
from modules.hostel.domain.errors import InvalidStateTransitionError
from modules.hostel.domain.state_machine import (
    transition_accommodation_request,
    transition_complaint,
    transition_extended_stay,
    transition_guest_room_booking,
    transition_leave_request,
)


# ---------------------------------------------------------------------------
# TC-WF-001: Accommodation request submitted (BW-HM-01 step-1)
# ---------------------------------------------------------------------------

class TestWF001SubmitAccommodationRequest:
    """test_id: TC-WF-001 | source_id: BW-HM-01 step-1"""

    def test_accommodation_request_initial_status_submitted(self):
        """test_id: TC-WF-001 | source_id: BW-HM-01 step-1
        Student submitting accommodation request starts in SUBMITTED state.
        """
        assert AccommodationRequestStatus.SUBMITTED == "submitted"

    def test_no_valid_transition_from_allotted_to_submitted(self):
        """test_id: TC-WF-001 | source_id: BW-HM-01 step-1
        Cannot go back to SUBMITTED once ALLOTTED – guards prevent backward transitions.
        """
        with pytest.raises(InvalidStateTransitionError):
            transition_accommodation_request(
                AccommodationRequestStatus.ALLOTTED,
                AccommodationRequestStatus.SUBMITTED,
            )


# ---------------------------------------------------------------------------
# TC-WF-002: Allotment decision progresses request to allotted (BW-HM-01 step-2)
# ---------------------------------------------------------------------------

class TestWF002AllotmentDecision:
    """test_id: TC-WF-002 | source_id: BW-HM-01 step-2"""

    def test_submitted_to_allotted_transition(self):
        """test_id: TC-WF-002 | source_id: BW-HM-01 step-2
        State transitions from submitted to allotted on batch allotment decision.
        """
        result = transition_accommodation_request(
            AccommodationRequestStatus.SUBMITTED,
            AccommodationRequestStatus.ALLOTTED,
        )
        assert result == AccommodationRequestStatus.ALLOTTED

    def test_allotment_active_status(self):
        """test_id: TC-WF-002 | source_id: BW-HM-01 step-2
        Room allotment record status starts as ACTIVE once created.
        """
        assert AllotmentStatus.ACTIVE == "active"


# ---------------------------------------------------------------------------
# TC-WF-003: Leave approval path (BW-HM-02)
# ---------------------------------------------------------------------------

class TestWF003LeaveApprovalPath:
    """test_id: TC-WF-003 | source_id: BW-HM-02 leave-approval-path"""

    def test_submitted_leave_to_approved(self):
        """test_id: TC-WF-003 | source_id: BW-HM-02 leave-approval-path
        Submitted leave transitions to approved on Caretaker approval decision.
        """
        result = transition_leave_request(
            LeaveStatus.SUBMITTED, LeaveStatus.APPROVED
        )
        assert result == LeaveStatus.APPROVED

    def test_approved_leave_status_terminal(self):
        """test_id: TC-WF-003 | source_id: BW-HM-02 leave-approval-path
        APPROVED is a terminal leave state; no further transitions allowed.
        """
        with pytest.raises(InvalidStateTransitionError):
            transition_leave_request(LeaveStatus.APPROVED, LeaveStatus.SUBMITTED)


# ---------------------------------------------------------------------------
# TC-WF-004: Leave rejection path (BW-HM-03)
# ---------------------------------------------------------------------------

class TestWF004LeaveRejectionPath:
    """test_id: TC-WF-004 | source_id: BW-HM-03 leave-rejection-path"""

    def test_submitted_leave_to_rejected(self):
        """test_id: TC-WF-004 | source_id: BW-HM-03 leave-rejection-path
        Submitted leave transitions to rejected on Caretaker rejection decision.
        """
        result = transition_leave_request(
            LeaveStatus.SUBMITTED, LeaveStatus.REJECTED
        )
        assert result == LeaveStatus.REJECTED

    def test_rejected_leave_status_terminal(self):
        """test_id: TC-WF-004 | source_id: BW-HM-03 leave-rejection-path
        REJECTED is a terminal leave state; cannot transition further.
        """
        with pytest.raises(InvalidStateTransitionError):
            transition_leave_request(LeaveStatus.REJECTED, LeaveStatus.APPROVED)


# ---------------------------------------------------------------------------
# TC-WF-005: Invalid leave transition guard (CW-HM-01)
# ---------------------------------------------------------------------------

class TestWF005InvalidLeaveTransition:
    """test_id: TC-WF-005 | source_id: CW-HM-01 invalid-transition"""

    def test_approved_to_rejected_raises(self):
        """test_id: TC-WF-005 | source_id: CW-HM-01 invalid-transition
        Approved leave cannot be directly rejected; raises InvalidStateTransitionError.
        """
        with pytest.raises(InvalidStateTransitionError):
            transition_leave_request(LeaveStatus.APPROVED, LeaveStatus.REJECTED)

    def test_rejected_to_rejected_raises(self):
        """test_id: TC-WF-005 | source_id: CW-HM-01 invalid-transition
        Rejected leave cannot re-transition to rejected.
        """
        with pytest.raises(InvalidStateTransitionError):
            transition_leave_request(LeaveStatus.REJECTED, LeaveStatus.REJECTED)


# ---------------------------------------------------------------------------
# TC-WF-006: Complaint resolution path (BW-HM-04)
# ---------------------------------------------------------------------------

class TestWF006ComplaintResolutionPath:
    """test_id: TC-WF-006 | source_id: BW-HM-04 complaint-resolution-path"""

    def test_submitted_complaint_to_resolved(self):
        """test_id: TC-WF-006 | source_id: BW-HM-04 complaint-resolution-path
        Submitted complaint transitions directly to resolved on Caretaker action.
        """
        result = transition_complaint(
            ComplaintStatus.SUBMITTED, ComplaintStatus.RESOLVED
        )
        assert result == ComplaintStatus.RESOLVED


# ---------------------------------------------------------------------------
# TC-WF-007: Complaint escalation path (BW-HM-05)
# ---------------------------------------------------------------------------

class TestWF007ComplaintEscalationPath:
    """test_id: TC-WF-007 | source_id: BW-HM-05 complaint-escalation-path"""

    def test_submitted_complaint_to_escalated(self):
        """test_id: TC-WF-007 | source_id: BW-HM-05 complaint-escalation-path
        Submitted complaint transitions to escalated to Warden.
        """
        result = transition_complaint(
            ComplaintStatus.SUBMITTED, ComplaintStatus.ESCALATED
        )
        assert result == ComplaintStatus.ESCALATED

    def test_escalated_complaint_to_resolved(self):
        """test_id: TC-WF-007 | source_id: BW-HM-05 complaint-escalation-path
        Escalated complaint can then be resolved by Warden.
        """
        result = transition_complaint(
            ComplaintStatus.ESCALATED, ComplaintStatus.RESOLVED
        )
        assert result == ComplaintStatus.RESOLVED


# ---------------------------------------------------------------------------
# TC-WF-008: Complaint unresolved then resolved path (CW-HM-02)
# ---------------------------------------------------------------------------

class TestWF008ComplaintUnresolvedToResolved:
    """test_id: TC-WF-008 | source_id: CW-HM-02 unresolved-then-resolved"""

    def test_submitted_to_unresolved(self):
        """test_id: TC-WF-008 | source_id: CW-HM-02 unresolved-then-resolved
        Step 1: submitted -> unresolved transition valid.
        """
        result = transition_complaint(
            ComplaintStatus.SUBMITTED, ComplaintStatus.UNRESOLVED
        )
        assert result == ComplaintStatus.UNRESOLVED

    def test_unresolved_to_resolved(self):
        """test_id: TC-WF-008 | source_id: CW-HM-02 unresolved-then-resolved
        Step 2: unresolved -> resolved transition valid.
        """
        result = transition_complaint(
            ComplaintStatus.UNRESOLVED, ComplaintStatus.RESOLVED
        )
        assert result == ComplaintStatus.RESOLVED

    def test_resolved_to_unresolved_invalid(self):
        """test_id: TC-WF-008 | source_id: CW-HM-02 unresolved-then-resolved
        Cannot move back from resolved to unresolved.
        """
        with pytest.raises(InvalidStateTransitionError):
            transition_complaint(ComplaintStatus.RESOLVED, ComplaintStatus.UNRESOLVED)


# ---------------------------------------------------------------------------
# TC-WF-009: Guest booking approval path (BW-HM-06)
# ---------------------------------------------------------------------------

class TestWF009GuestBookingApproval:
    """test_id: TC-WF-009 | source_id: BW-HM-06 guest-booking-approval-path"""

    def test_submitted_guest_booking_to_approved(self):
        """test_id: TC-WF-009 | source_id: BW-HM-06 guest-booking-approval-path
        Submitted guest room booking transitions to approved.
        """
        result = transition_guest_room_booking(
            GuestRoomBookingStatus.SUBMITTED, GuestRoomBookingStatus.APPROVED
        )
        assert result == GuestRoomBookingStatus.APPROVED


# ---------------------------------------------------------------------------
# TC-WF-010: Guest booking rejection path (BW-HM-07)
# ---------------------------------------------------------------------------

class TestWF010GuestBookingRejection:
    """test_id: TC-WF-010 | source_id: BW-HM-07 guest-booking-rejection-path"""

    def test_submitted_guest_booking_to_rejected(self):
        """test_id: TC-WF-010 | source_id: BW-HM-07 guest-booking-rejection-path
        Submitted guest room booking transitions to rejected.
        """
        result = transition_guest_room_booking(
            GuestRoomBookingStatus.SUBMITTED, GuestRoomBookingStatus.REJECTED
        )
        assert result == GuestRoomBookingStatus.REJECTED

    def test_approved_to_rejected_invalid_guest_booking(self):
        """test_id: TC-WF-010 | source_id: BW-HM-07 guest-booking-rejection-path
        Already approved booking cannot be rejected; guard enforced.
        """
        with pytest.raises(InvalidStateTransitionError):
            transition_guest_room_booking(
                GuestRoomBookingStatus.APPROVED, GuestRoomBookingStatus.REJECTED
            )


# ---------------------------------------------------------------------------
# TC-WF-011: Extended stay approval path (BW-HM-08)
# ---------------------------------------------------------------------------

class TestWF011ExtendedStayApproval:
    """test_id: TC-WF-011 | source_id: BW-HM-08 extended-stay-approval-path"""

    def test_submitted_extended_stay_to_approved(self):
        """test_id: TC-WF-011 | source_id: BW-HM-08 extended-stay-approval-path
        Submitted extended stay transitions to approved on Warden decision.
        """
        result = transition_extended_stay(
            ExtendedStayStatus.SUBMITTED, ExtendedStayStatus.APPROVED
        )
        assert result == ExtendedStayStatus.APPROVED


# ---------------------------------------------------------------------------
# TC-WF-012: Extended stay rejection path (BW-HM-09)
# ---------------------------------------------------------------------------

class TestWF012ExtendedStayRejection:
    """test_id: TC-WF-012 | source_id: BW-HM-09 extended-stay-rejection-path"""

    def test_submitted_extended_stay_to_rejected(self):
        """test_id: TC-WF-012 | source_id: BW-HM-09 extended-stay-rejection-path
        Submitted extended stay transitions to rejected on Warden decision.
        """
        result = transition_extended_stay(
            ExtendedStayStatus.SUBMITTED, ExtendedStayStatus.REJECTED
        )
        assert result == ExtendedStayStatus.REJECTED

    def test_approved_to_rejected_invalid_extended_stay(self):
        """test_id: TC-WF-012 | source_id: BW-HM-09 extended-stay-rejection-path
        Approved extended stay cannot be transitioned to rejected.
        """
        with pytest.raises(InvalidStateTransitionError):
            transition_extended_stay(
                ExtendedStayStatus.APPROVED, ExtendedStayStatus.REJECTED
            )
