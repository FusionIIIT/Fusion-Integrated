"""State transitions and workflow enforcement for Hostel Management."""

from .constants import (
    AccommodationStatus,
    ComplaintStatus,
    ExtendedStayStatus,
    GuestRoomStatus,
    LeaveStatus,
)
from .errors import InvalidStateTransitionError


class WorkflowStateMachine:
    """Enforces authoritative state transitions for all HM workflows."""

    # BW-HM-01: Accommodation Request to Initial Allotment
    ACCOMMODATION_TRANSITIONS = {
        AccommodationStatus.SUBMITTED: {
            AccommodationStatus.ALLOTTED,
            AccommodationStatus.REJECTED,
            AccommodationStatus.CANCELLED,
        },
    }

    # CW-HM-01 (BW-HM-02 / BW-HM-03): Leave Request Decision
    LEAVE_TRANSITIONS = {
        LeaveStatus.SUBMITTED: {
            LeaveStatus.APPROVED,
            LeaveStatus.REJECTED,
        },
    }

    # CW-HM-02 (BW-HM-04 / BW-HM-05): Complaint Handling and Escalation
    COMPLAINT_TRANSITIONS = {
        ComplaintStatus.SUBMITTED: {
            ComplaintStatus.IN_PROGRESS,
            ComplaintStatus.RESOLVED,
            ComplaintStatus.ESCALATED,
        },
        ComplaintStatus.IN_PROGRESS: {
            ComplaintStatus.RESOLVED,
            ComplaintStatus.ESCALATED,
        },
        ComplaintStatus.ESCALATED: {
            ComplaintStatus.RESOLVED,
        },
    }

    # CW-HM-03 (BW-HM-06 / BW-HM-07): Guest Room Booking Decision
    GUEST_ROOM_TRANSITIONS = {
        GuestRoomStatus.REQUESTED: {
            GuestRoomStatus.APPROVED,
            GuestRoomStatus.REJECTED,
            GuestRoomStatus.CANCELLED,
        },
    }

    # CW-HM-04 (BW-HM-08 / BW-HM-09): Extended Stay Request Decision
    EXTENDED_STAY_TRANSITIONS = {
        ExtendedStayStatus.SUBMITTED: {
            ExtendedStayStatus.APPROVED,
            ExtendedStayStatus.REJECTED,
        },
    }

    @classmethod
    def validate_accommodation_transition(cls, from_state: str, to_state: str) -> None:
        allowed = cls.ACCOMMODATION_TRANSITIONS.get(from_state, set())
        if to_state not in allowed:
            raise InvalidStateTransitionError("BW-HM-01", from_state, to_state)

    @classmethod
    def validate_leave_transition(cls, from_state: str, to_state: str) -> None:
        allowed = cls.LEAVE_TRANSITIONS.get(from_state, set())
        if to_state not in allowed:
            raise InvalidStateTransitionError("CW-HM-01", from_state, to_state)

    @classmethod
    def validate_complaint_transition(cls, from_state: str, to_state: str) -> None:
        allowed = cls.COMPLAINT_TRANSITIONS.get(from_state, set())
        if to_state not in allowed:
            raise InvalidStateTransitionError("CW-HM-02", from_state, to_state)

    @classmethod
    def validate_guest_room_transition(cls, from_state: str, to_state: str) -> None:
        allowed = cls.GUEST_ROOM_TRANSITIONS.get(from_state, set())
        if to_state not in allowed:
            raise InvalidStateTransitionError("CW-HM-03", from_state, to_state)

    @classmethod
    def validate_extended_stay_transition(cls, from_state: str, to_state: str) -> None:
        allowed = cls.EXTENDED_STAY_TRANSITIONS.get(from_state, set())
        if to_state not in allowed:
            raise InvalidStateTransitionError("CW-HM-04", from_state, to_state)
