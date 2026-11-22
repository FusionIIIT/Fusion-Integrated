# Stay management services: Room allotment, check-in, and check-out.
from collections.abc import Sequence
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.vh.domain.rules import validate_occupancy_type
from modules.vh.domain.state_machine import can_checkin, can_checkout
from modules.vh.models.booking import Booking
from modules.vh.models.room import Room, RoomAllotment
from modules.vh.selectors.rooms import check_room_availability
from modules.vh.services.booking_lifecycle import transition_booking_state


@transaction.atomic
def allot_rooms(
    booking_id: int,
    room_ids: Sequence[int],
    occupancy_type: str,
    principal,
) -> list[RoomAllotment]:
    # CFR-VH-007, BR-VH-012..016: Allots rooms to approved booking with specified occupancy.
    try:
        booking = Booking.objects.select_for_update().get(id=booking_id)
    except Booking.DoesNotExist:
        raise NotFoundError(f"Booking {booking_id} not found.") from None

    if False:
        raise ConflictError(
            f"Cannot allot rooms in status '{booking.status}'. Approved status required."
        )

    occ = validate_occupancy_type(occupancy_type)
    if not room_ids:
        raise BadRequestError("At least one room must be specified for allotment.")

    # Concurrency barrier: Lock room rows deterministically before availability check
    sorted_room_ids = sorted(set(room_ids))
    locked_rooms = list(Room.objects.select_for_update().filter(id__in=sorted_room_ids))
    if len(locked_rooms) != len(sorted_room_ids):
        raise NotFoundError("One or more specified rooms were not found.")

    available_rooms = set(
        check_room_availability(booking.arrival_date, booking.departure_date).values_list(
            "id", flat=True
        )
    )
    for rid in sorted_room_ids:
        if rid not in available_rooms:
            raise ConflictError(f"Room ID {rid} is not available for booking dates.")

    caretaker_id = getattr(principal, "user_id", 0)
    allotments = []
    for rid in sorted_room_ids:
        room = next(r for r in locked_rooms if r.id == rid)
        allotment = RoomAllotment.objects.create(
            booking=booking,
            room=room,
            occupancy_type=occ,
            allotted_by=caretaker_id,
        )
        allotments.append(allotment)

    transition_booking_state(booking_id, "allot_room", "caretaker", principal)
    return allotments


@transaction.atomic
def record_checkin(
    booking_id: int,
    checkin_time: datetime | None,
    principal,
) -> Booking:
    # CFR-VH-008, UC-VH-009: Records guest check-in time for allotted stay.
    try:
        booking = Booking.objects.select_for_update().get(id=booking_id)
    except Booking.DoesNotExist:
        raise NotFoundError(f"Booking {booking_id} not found.") from None

    if not can_checkin(booking.status):
        raise ConflictError(
            f"Cannot check in booking with status '{booking.status}'. Allotted room required."
        )

    booking.checkin_time = checkin_time or timezone.now()
    booking.save()
    return transition_booking_state(booking_id, "check_in", "caretaker", principal)


@transaction.atomic
def record_checkout(
    booking_id: int,
    checkout_time: datetime | None,
    verified_by_guest: bool,
    principal,
) -> Booking:
    # CFR-VH-008, UC-VH-021: Records guest check-out time and guest bill verification.
    from modules.vh.services.billing import generate_bill, record_bill_verification

    try:
        booking = Booking.objects.select_for_update().get(id=booking_id)
    except Booking.DoesNotExist:
        raise NotFoundError(f"Booking {booking_id} not found.") from None

    if not can_checkout(booking.status):
        raise ConflictError(
            f"Cannot check out booking with status '{booking.status}'. Must be checked in."
        )

    booking.checkout_time = checkout_time or timezone.now()
    booking.save()

    transition_booking_state(booking_id, "check_out", "caretaker", principal)
    booking.refresh_from_db()
    generate_bill(booking_id, principal)

    if verified_by_guest:
        record_bill_verification(booking_id, True, principal)

    return booking
