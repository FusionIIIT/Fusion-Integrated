from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .constants import (
    AccommodationRequestStatus,
    AllotmentStatus,
    ComplaintStatus,
    ExtendedStayStatus,
    GuestRoomBookingStatus,
    LeaveStatus,
)
from .errors import InvalidTransitionError


@dataclass(frozen=True)
class Transition:
    frm: str
    to: str
    required_role: str | None = None
    guards: tuple[Callable[..., bool], ...] = ()
    effects: tuple[str, ...] = ()


# --- Leave State Machine (BW-HM-02, BW-HM-03, CW-HM-01) ---
LEAVE_TRANSITIONS: tuple[Transition, ...] = (
    Transition(
        frm=LeaveStatus.PENDING,
        to=LeaveStatus.APPROVED,
        required_role="caretaker",
        effects=("notify_student_leave_approved",),
    ),
    Transition(
        frm=LeaveStatus.PENDING,
        to=LeaveStatus.REJECTED,
        required_role="caretaker",
        effects=("notify_student_leave_rejected",),
    ),
    Transition(
        frm=LeaveStatus.PENDING,
        to=LeaveStatus.CANCELLED,
        required_role="student",
        effects=("notify_leave_cancelled",),
    ),
)
LEAVE_TERMINAL: set[str] = {LeaveStatus.APPROVED, LeaveStatus.REJECTED, LeaveStatus.CANCELLED}


# --- Complaint State Machine (BW-HM-04, BW-HM-05, CW-HM-02) ---
COMPLAINT_TRANSITIONS: tuple[Transition, ...] = (
    Transition(
        frm=ComplaintStatus.OPEN,
        to=ComplaintStatus.IN_PROGRESS,
        required_role="caretaker",
        effects=("notify_complaint_assigned",),
    ),
    Transition(
        frm=ComplaintStatus.OPEN,
        to=ComplaintStatus.ESCALATED,
        required_role="caretaker",
        effects=("notify_warden_escalated_complaint",),
    ),
    Transition(
        frm=ComplaintStatus.OPEN,
        to=ComplaintStatus.REJECTED,
        required_role="caretaker",
        effects=("notify_complaint_rejected",),
    ),
    Transition(
        frm=ComplaintStatus.IN_PROGRESS,
        to=ComplaintStatus.RESOLVED,
        required_role="caretaker",
        effects=("notify_complaint_resolved",),
    ),
    Transition(
        frm=ComplaintStatus.IN_PROGRESS,
        to=ComplaintStatus.ESCALATED,
        required_role="caretaker",
        effects=("notify_warden_escalated_complaint",),
    ),
    Transition(
        frm=ComplaintStatus.ESCALATED,
        to=ComplaintStatus.RESOLVED,
        required_role="warden",
        effects=("notify_complaint_resolved_by_warden",),
    ),
    Transition(
        frm=ComplaintStatus.RESOLVED,
        to=ComplaintStatus.CLOSED,
        required_role="student",
        effects=("notify_complaint_closed",),
    ),
    Transition(
        frm=ComplaintStatus.RESOLVED,
        to=ComplaintStatus.OPEN,  # Reopen
        required_role="student",
        effects=("notify_complaint_reopened",),
    ),
)
COMPLAINT_TERMINAL: set[str] = {ComplaintStatus.CLOSED, ComplaintStatus.REJECTED}


# --- Guest Room Booking State Machine (BW-HM-06, BW-HM-07, CW-HM-03) ---
GUEST_ROOM_TRANSITIONS: tuple[Transition, ...] = (
    Transition(
        frm=GuestRoomBookingStatus.PENDING,
        to=GuestRoomBookingStatus.APPROVED,
        required_role="caretaker",
        effects=("notify_guest_room_approved",),
    ),
    Transition(
        frm=GuestRoomBookingStatus.PENDING,
        to=GuestRoomBookingStatus.REJECTED,
        required_role="caretaker",
        effects=("notify_guest_room_rejected",),
    ),
    Transition(
        frm=GuestRoomBookingStatus.APPROVED,
        to=GuestRoomBookingStatus.CHECKED_IN,
        required_role="caretaker",
    ),
    Transition(
        frm=GuestRoomBookingStatus.CHECKED_IN,
        to=GuestRoomBookingStatus.CHECKED_OUT,
        required_role="caretaker",
    ),
    Transition(
        frm=GuestRoomBookingStatus.PENDING,
        to=GuestRoomBookingStatus.CANCELLED,
        required_role="student",
    ),
)
GUEST_ROOM_TERMINAL: set[str] = {
    GuestRoomBookingStatus.REJECTED,
    GuestRoomBookingStatus.CHECKED_OUT,
    GuestRoomBookingStatus.CANCELLED,
}


# --- Extended Stay State Machine (BW-HM-08, BW-HM-09, CW-HM-04) ---
EXTENDED_STAY_TRANSITIONS: tuple[Transition, ...] = (
    Transition(
        frm=ExtendedStayStatus.PENDING,
        to=ExtendedStayStatus.APPROVED,
        required_role="warden",
        effects=("notify_extended_stay_approved",),
    ),
    Transition(
        frm=ExtendedStayStatus.PENDING,
        to=ExtendedStayStatus.REJECTED,
        required_role="warden",
        effects=("notify_extended_stay_rejected",),
    ),
    Transition(
        frm=ExtendedStayStatus.PENDING,
        to=ExtendedStayStatus.CANCELLED,
        required_role="student",
    ),
)
EXTENDED_STAY_TERMINAL: set[str] = {
    ExtendedStayStatus.APPROVED,
    ExtendedStayStatus.REJECTED,
    ExtendedStayStatus.CANCELLED,
}


# --- Accommodation Request State Machine (BW-HM-01) ---
ACCOMMODATION_REQUEST_TRANSITIONS: tuple[Transition, ...] = (
    Transition(
        frm=AccommodationRequestStatus.PENDING,
        to=AccommodationRequestStatus.APPROVED,
        required_role="super_admin",
    ),
    Transition(
        frm=AccommodationRequestStatus.PENDING,
        to=AccommodationRequestStatus.REJECTED,
        required_role="super_admin",
    ),
    Transition(
        frm=AccommodationRequestStatus.APPROVED,
        to=AccommodationRequestStatus.ALLOCATED,
        required_role="super_admin",
        effects=("notify_room_allocated",),
    ),
    Transition(
        frm=AccommodationRequestStatus.PENDING,
        to=AccommodationRequestStatus.CANCELLED,
        required_role="student",
    ),
)


# --- Allotment State Machine (HM-UC-007) ---
ALLOTMENT_TRANSITIONS: tuple[Transition, ...] = (
    Transition(
        frm=AllotmentStatus.ACTIVE,
        to=AllotmentStatus.VACATED,
        required_role="super_admin",
        effects=("notify_room_vacated", "release_room_bed"),
    ),
    Transition(
        frm=AllotmentStatus.ACTIVE,
        to=AllotmentStatus.TRANSFERRED,
        required_role="super_admin",
        effects=("transfer_room_bed",),
    ),
)


def validate_transition(
    transitions: tuple[Transition, ...],
    current_status: str,
    target_status: str,
    actor_role: str | None = None,
    context: dict[str, Any] | None = None,
) -> Transition:
    """Validate if transition is legal and authorized by actor role."""
    matched = [t for t in transitions if t.frm == current_status and t.to == target_status]
    if not matched:
        raise InvalidTransitionError(
            f"Illegal state transition from '{current_status}' to '{target_status}'"
        )
    transition = matched[0]

    # Check role if required
    if (
        transition.required_role
        and actor_role
        and actor_role not in ("super_admin", transition.required_role)
    ):
        raise InvalidTransitionError(
            f"Role '{actor_role}' is not authorized to transition from "
            f"'{current_status}' to '{target_status}'. Required: '{transition.required_role}'"
        )

    # Check custom guards
    ctx = context or {}
    for guard in transition.guards:
        if not guard(ctx):
            raise InvalidTransitionError(
                f"Transition guard '{guard.__name__}' failed for transition to '{target_status}'"
            )

    return transition


def can_transition(
    transitions: tuple[Transition, ...],
    current_status: str,
    target_status: str,
) -> bool:
    """Check if any transition exists between current and target status."""
    return any(t.frm == current_status and t.to == target_status for t in transitions)
