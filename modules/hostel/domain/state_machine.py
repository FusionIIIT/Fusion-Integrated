"""Authoritative State-Transition implementations for HM Workflows (pure Python).

Workflows covered:
- BW-HM-01: Accommodation Request to Initial Allotment
- BW-HM-02 / BW-HM-03 / CW-HM-01: Leave Request Decision
- BW-HM-04 / BW-HM-05 / CW-HM-02: Complaint Handling and Escalation
- BW-HM-06 / BW-HM-07 / CW-HM-03: Guest-Room Booking Decision
- BW-HM-08 / BW-HM-09 / CW-HM-04: Extended-Stay Request Decision
"""

from modules.hostel.domain.enums import (
    AccommodationRequestStatus,
    ComplaintStatus,
    ExtendedStayStatus,
    GuestRoomBookingStatus,
    LeaveStatus,
)
from modules.hostel.domain.errors import InvalidStateTransitionError


def transition_accommodation_request(current_status: str, target_status: str) -> str:
    """Enforces BW-HM-01 state transitions:
    No active -> SUBMITTED -> ALLOTTED or REJECTED / CANCELLED.
    """
    valid_transitions = {
        AccommodationRequestStatus.SUBMITTED: {
            AccommodationRequestStatus.ALLOTTED,
            AccommodationRequestStatus.REJECTED,
            AccommodationRequestStatus.CANCELLED,
        },
    }
    allowed = valid_transitions.get(current_status, set())
    if target_status not in allowed:
        raise InvalidStateTransitionError(
            f"Invalid accommodation request transition from '{current_status}' to '{target_status}'"
        )
    return target_status


def transition_leave_request(current_status: str, target_status: str) -> str:
    """Enforces BW-HM-02, BW-HM-03, CW-HM-01 state transitions:
    SUBMITTED -> APPROVED or REJECTED.
    """
    valid_transitions = {
        LeaveStatus.SUBMITTED: {
            LeaveStatus.APPROVED,
            LeaveStatus.REJECTED,
        },
    }
    allowed = valid_transitions.get(current_status, set())
    if target_status not in allowed:
        raise InvalidStateTransitionError(
            f"Invalid leave request transition from '{current_status}' to '{target_status}'"
        )
    return target_status


def transition_complaint(current_status: str, target_status: str) -> str:
    """Enforces BW-HM-04, BW-HM-05, CW-HM-02 state transitions:
    SUBMITTED -> RESOLVED, UNRESOLVED, ESCALATED
    UNRESOLVED -> RESOLVED, ESCALATED
    ESCALATED -> RESOLVED
    """
    valid_transitions = {
        ComplaintStatus.SUBMITTED: {
            ComplaintStatus.RESOLVED,
            ComplaintStatus.UNRESOLVED,
            ComplaintStatus.ESCALATED,
        },
        ComplaintStatus.UNRESOLVED: {
            ComplaintStatus.RESOLVED,
            ComplaintStatus.ESCALATED,
        },
        ComplaintStatus.ESCALATED: {
            ComplaintStatus.RESOLVED,
        },
    }
    allowed = valid_transitions.get(current_status, set())
    if target_status not in allowed:
        raise InvalidStateTransitionError(
            f"Invalid complaint transition from '{current_status}' to '{target_status}'"
        )
    return target_status


def transition_guest_room_booking(current_status: str, target_status: str) -> str:
    """Enforces BW-HM-06, BW-HM-07, CW-HM-03 state transitions:
    SUBMITTED -> APPROVED or REJECTED.
    """
    valid_transitions = {
        GuestRoomBookingStatus.SUBMITTED: {
            GuestRoomBookingStatus.APPROVED,
            GuestRoomBookingStatus.REJECTED,
        },
    }
    allowed = valid_transitions.get(current_status, set())
    if target_status not in allowed:
        raise InvalidStateTransitionError(
            f"Invalid guest room booking transition from '{current_status}' to '{target_status}'"
        )
    return target_status


def transition_extended_stay(current_status: str, target_status: str) -> str:
    """Enforces BW-HM-08, BW-HM-09, CW-HM-04 state transitions:
    SUBMITTED -> APPROVED or REJECTED.
    """
    valid_transitions = {
        ExtendedStayStatus.SUBMITTED: {
            ExtendedStayStatus.APPROVED,
            ExtendedStayStatus.REJECTED,
        },
    }
    allowed = valid_transitions.get(current_status, set())
    if target_status not in allowed:
        raise InvalidStateTransitionError(
            f"Invalid extended-stay transition from '{current_status}' to '{target_status}'"
        )
    return target_status
