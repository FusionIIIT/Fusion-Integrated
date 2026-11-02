"""Guest room booking services (3.6, CFR-HM-017, BR-HM-018, BR-HM-019, CW-HM-03)."""

from datetime import date
from django.db import transaction
from django.utils import timezone
from ..domain.constants import GuestRoomStatus
from ..domain.errors import HostelDomainError, InactiveHostelError
from ..domain.state_machine import WorkflowStateMachine
from ..models import GuestRoomBooking, Hostel, Room
from .notification_service import create_notification


@transaction.atomic
def submit_guest_room_request(
    student_user_id: int,
    student_roll_number: str,
    student_name: str,
    hostel_id: int,
    guest_name: str,
    guest_relation: str,
    guest_gender: str,
    check_in_date: date,
    check_out_date: date,
    number_of_guests: int = 1,
    reason: str = "",
) -> GuestRoomBooking:
    """Student submits guest room booking request (HM-UC-020)."""
    hostel = Hostel.objects.filter(id=hostel_id).first()
    if not hostel:
        raise HostelDomainError(f"Hostel {hostel_id} not found.", code="not_found")
    if not hostel.is_active:
        raise InactiveHostelError(hostel.name)
    if check_in_date > check_out_date:
        raise HostelDomainError("Check-in date cannot be after check-out date.", code="invalid_dates")

    booking = GuestRoomBooking.objects.create(
        hostel=hostel,
        student_user_id=student_user_id,
        student_roll_number=student_roll_number.strip(),
        student_name=student_name.strip(),
        guest_name=guest_name.strip(),
        guest_relation=guest_relation.strip(),
        guest_gender=guest_gender.strip(),
        check_in_date=check_in_date,
        check_out_date=check_out_date,
        number_of_guests=number_of_guests,
        reason=reason.strip(),
        status=GuestRoomStatus.REQUESTED.value,
    )

    create_notification(
        recipient_user_id=student_user_id,
        event_type="guest_booking_submitted",
        title="Guest Room Booking Requested",
        message=f"Your booking request for {guest_name} ({check_in_date} to {check_out_date}) is submitted.",
        reference_id=str(booking.id),
    )
    return booking


@transaction.atomic
def record_guest_room_decision(
    caretaker_user_id: int,
    booking_id: int,
    decision: str,  # 'approved' or 'rejected'
    assigned_room_id: int | None = None,
    remarks: str = "",
) -> GuestRoomBooking:
    """Caretaker approves or rejects guest room booking (HM-UC-021, CW-HM-03)."""
    booking = GuestRoomBooking.objects.select_for_update().select_related("hostel").filter(id=booking_id).first()
    if not booking:
        raise HostelDomainError(f"Booking {booking_id} not found.", code="not_found")

    WorkflowStateMachine.validate_guest_room_transition(booking.status, decision)

    if decision == GuestRoomStatus.APPROVED.value and assigned_room_id:
        room = Room.objects.filter(id=assigned_room_id, hostel=booking.hostel).first()
        if not room:
            raise HostelDomainError(f"Assigned room {assigned_room_id} not found in {booking.hostel.name}.")
        booking.assigned_room = room

    booking.status = decision
    booking.decision_by_user_id = caretaker_user_id
    booking.decision_at = timezone.now()
    booking.decision_remarks = remarks.strip()
    booking.save()

    create_notification(
        recipient_user_id=booking.student_user_id,
        event_type=f"guest_booking_{decision}",
        title=f"Guest Room Booking {decision.capitalize()}",
        message=f"Your guest booking for {booking.guest_name} has been {decision}.",
        reference_id=str(booking.id),
    )

    return booking
