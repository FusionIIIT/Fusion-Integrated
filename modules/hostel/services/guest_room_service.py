"""Guest room booking services (CFR-HM-019..021, BW-HM-06/07, CW-HM-03, BR-HM-018, 019)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from modules.hostel.domain.constants import GuestRoomBookingStatus, NotificationEventType
from modules.hostel.domain.errors import ValidationError
from modules.hostel.domain.state_machine import GUEST_ROOM_TRANSITIONS, validate_transition
from modules.hostel.models import GuestRoomBooking, Hostel
from modules.hostel.services.notification_service import emit_notification


@transaction.atomic
def submit_guest_room_booking(
    student_user_id: int,
    hostel_id: int,
    guest_name: str,
    relationship: str,
    num_guests: int,
    check_in_date: date,
    check_out_date: date,
    purpose: str,
) -> GuestRoomBooking:
    """CFR-HM-019, HM-UC-020: Student requests guest room booking."""
    if check_in_date > check_out_date:
        raise ValidationError("Check-in date cannot be after check-out date")
    if num_guests <= 0:
        raise ValidationError("Number of guests must be at least 1")
    if not guest_name or not guest_name.strip():
        raise ValidationError("Guest name is required")

    hostel = Hostel.objects.get(id=hostel_id)

    return GuestRoomBooking.objects.create(
        student_user_id=student_user_id,
        hostel=hostel,
        guest_name=guest_name.strip(),
        relationship=relationship.strip(),
        num_guests=num_guests,
        check_in_date=check_in_date,
        check_out_date=check_out_date,
        purpose=purpose.strip(),
        status=GuestRoomBookingStatus.PENDING.value,
    )


@transaction.atomic
def decide_guest_room_booking(
    booking_id: int,
    decision: str,  # 'approved' or 'rejected'
    caretaker_user_id: int | None = None,
    allocated_room_number: str = "",
    charges: Decimal | float = 0.00,
    remarks: str = "",
) -> GuestRoomBooking:
    """CFR-HM-020, HM-UC-021, BW-HM-06/07, CW-HM-03: Caretaker reviews booking."""
    booking = GuestRoomBooking.objects.select_for_update().get(id=booking_id)

    validate_transition(
        transitions=GUEST_ROOM_TRANSITIONS,
        current_status=booking.status,
        target_status=decision,
        actor_role="caretaker",
    )

    booking.status = decision
    booking.allocated_room_number = allocated_room_number.strip()
    booking.charges = Decimal(str(charges))
    booking.decided_by_user_id = caretaker_user_id
    booking.decided_at = timezone.now()
    booking.decision_remarks = remarks.strip()
    booking.save(
        update_fields=[
            "status",
            "allocated_room_number",
            "charges",
            "decided_by_user_id",
            "decided_at",
            "decision_remarks",
            "updated_at",
        ]
    )

    emit_notification(
        recipient_user_id=booking.student_user_id,
        title=f"Guest Room Booking {decision.capitalize()}",
        message=f"Booking for {booking.guest_name} was {decision}. Room: {allocated_room_number}",
        event_type=NotificationEventType.GUEST_BOOKING_DECIDED,
        link="/hostel/guest-rooms",
    )

    return booking
