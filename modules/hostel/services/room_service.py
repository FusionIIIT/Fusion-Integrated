"""Room management and individual room exchange services (CFR-HM-006, 007, HM-UC-009, 010)."""

from __future__ import annotations

from django.db import transaction

from modules.hostel.domain.constants import (
    AllotmentStatus,
    NotificationEventType,
    RoomExchangeStatus,
    RoomStatus,
)
from modules.hostel.domain.errors import ValidationError
from modules.hostel.models import Hostel, Room, RoomAllotment, RoomExchangeRequest
from modules.hostel.services.notification_service import emit_notification


@transaction.atomic
def create_room(
    hostel_id: int,
    room_number: str,
    floor: int = 0,
    capacity: int = 2,
    status: str = RoomStatus.AVAILABLE.value,
    remarks: str = "",
) -> Room:
    """Create a new room in a hostel."""
    hostel = Hostel.objects.get(id=hostel_id)
    room_num_clean = room_number.strip().upper()
    if Room.objects.filter(hostel=hostel, room_number=room_num_clean).exists():
        raise ValidationError(f"Room '{room_num_clean}' already exists in {hostel.code}")

    if capacity <= 0:
        raise ValidationError("Room capacity must be greater than zero")

    return Room.objects.create(
        hostel=hostel,
        room_number=room_num_clean,
        floor=floor,
        capacity=capacity,
        current_occupancy=0,
        status=status,
        remarks=remarks.strip(),
    )


@transaction.atomic
def update_room_status(
    room_id: int,
    status: str,
    remarks: str = "",
) -> Room:
    """CFR-HM-006: Caretaker updates room maintenance or availability status."""
    room = Room.objects.get(id=room_id)
    room.status = status
    if remarks:
        room.remarks = remarks.strip()
    room.save(update_fields=["status", "remarks", "updated_at"])
    return room


@transaction.atomic
def execute_room_exchange(
    requester_student_user_id: int,
    target_student_user_id: int,
    reason: str,
    caretaker_user_id: int | None = None,
) -> RoomExchangeRequest:
    """CFR-HM-007, HM-UC-010: Caretaker records individual student room exchange."""
    # Fetch active allotments for both students
    alt_req = (
        RoomAllotment.objects.select_for_update()
        .select_related("room", "hostel")
        .get(student_user_id=requester_student_user_id, status=AllotmentStatus.ACTIVE.value)
    )
    alt_tgt = (
        RoomAllotment.objects.select_for_update()
        .select_related("room", "hostel")
        .get(student_user_id=target_student_user_id, status=AllotmentStatus.ACTIVE.value)
    )

    if alt_req.hostel_id != alt_tgt.hostel_id:
        raise ValidationError("Room exchange must be within the same assigned hostel")

    room_req = alt_req.room
    room_tgt = alt_tgt.room

    # Swap rooms
    alt_req.room = room_tgt
    alt_tgt.room = room_req
    alt_req.save(update_fields=["room", "updated_at"])
    alt_tgt.save(update_fields=["room", "updated_at"])

    exchange_req = RoomExchangeRequest.objects.create(
        requester_student_user_id=requester_student_user_id,
        target_student_user_id=target_student_user_id,
        from_room=room_req,
        to_room=room_tgt,
        reason=reason.strip(),
        status=RoomExchangeStatus.COMPLETED.value,
        approved_by_user_id=caretaker_user_id,
        decision_remarks=f"Completed exchange by Caretaker {caretaker_user_id}",
    )

    emit_notification(
        recipient_user_id=requester_student_user_id,
        title="Room Exchange Completed",
        message=f"You have been swapped to Room {room_tgt.room_number}.",
        event_type=NotificationEventType.ALLOTMENT_UPDATED,
    )
    emit_notification(
        recipient_user_id=target_student_user_id,
        title="Room Exchange Completed",
        message=f"You have been swapped to Room {room_req.room_number}.",
        event_type=NotificationEventType.ALLOTMENT_UPDATED,
    )

    return exchange_req
