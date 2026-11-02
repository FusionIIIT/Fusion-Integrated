"""Room allotment and vacation services (CFR-HM-003..005, BR-HM-008..010, BW-HM-01)."""

from __future__ import annotations

from datetime import date

from django.db import transaction
from django.utils import timezone

from modules.hostel.domain.constants import (
    AccommodationRequestStatus,
    AllotmentStatus,
    NotificationEventType,
    RoomStatus,
)
from modules.hostel.domain.errors import (
    CapacityExceededError,
    DuplicateAllotmentError,
    ValidationError,
)
from modules.hostel.models import AccommodationRequest, Hostel, Room, RoomAllotment
from modules.hostel.services.notification_service import emit_notification


@transaction.atomic
def submit_accommodation_request(
    student_user_id: int,
    preferred_hostel_id: int | None = None,
    room_type_preference: str = "",
    academic_year: str = "2026-27",
    semester: int = 1,
    reason: str = "",
) -> AccommodationRequest:
    """CFR-HM-003, HM-UC-005, BW-HM-01: Student submits accommodation request."""
    # Check if student already has an active allotment
    if RoomAllotment.objects.filter(
        student_user_id=student_user_id, status=AllotmentStatus.ACTIVE.value
    ).exists():
        raise DuplicateAllotmentError("Student already has an active room allotment")

    # Check for pending request
    if AccommodationRequest.objects.filter(
        student_user_id=student_user_id, status=AccommodationRequestStatus.PENDING.value
    ).exists():
        raise ValidationError("Student already has a pending accommodation request")

    pref_hostel = None
    if preferred_hostel_id:
        pref_hostel = Hostel.objects.filter(id=preferred_hostel_id, is_active=True).first()

    return AccommodationRequest.objects.create(
        student_user_id=student_user_id,
        preferred_hostel=pref_hostel,
        room_type_preference=room_type_preference.strip(),
        academic_year=academic_year.strip(),
        semester=semester,
        reason=reason.strip(),
        status=AccommodationRequestStatus.PENDING.value,
    )


@transaction.atomic
def allot_room(
    student_user_id: int,
    hostel_id: int,
    room_id: int,
    bed_number: str = "A",
    allotment_date: date | None = None,
    allotted_by_user_id: int | None = None,
    linked_request_id: int | None = None,
) -> RoomAllotment:
    """CFR-HM-004, HM-UC-006, BR-HM-010: Allot a student to a room and update capacity."""
    # Check if student already allotted
    if RoomAllotment.objects.filter(
        student_user_id=student_user_id, status=AllotmentStatus.ACTIVE.value
    ).exists():
        raise DuplicateAllotmentError("Student already holds an active room allotment")

    room = Room.objects.select_for_update().get(id=room_id, hostel_id=hostel_id)

    # Check capacity limit (BR-HM-010)
    if room.current_occupancy >= room.capacity:
        raise CapacityExceededError(
            f"Room {room.room_number} in {room.hostel.code} is at full capacity ({room.capacity})"
        )

    if room.status in (RoomStatus.MAINTENANCE.value, RoomStatus.BLOCKED.value):
        raise ValidationError(f"Room {room.room_number} is currently {room.status}")

    # Create allotment
    allotment = RoomAllotment.objects.create(
        student_user_id=student_user_id,
        hostel=room.hostel,
        room=room,
        bed_number=bed_number.strip() or "A",
        allotment_date=allotment_date or timezone.now().date(),
        status=AllotmentStatus.ACTIVE.value,
        allotted_by_user_id=allotted_by_user_id,
    )

    # Update room occupancy
    room.current_occupancy += 1
    if room.current_occupancy >= room.capacity:
        room.status = RoomStatus.FULL.value
    else:
        room.status = RoomStatus.OCCUPIED.value
    room.save(update_fields=["current_occupancy", "status", "updated_at"])

    # If linked to an accommodation request, mark as allocated
    if linked_request_id:
        AccommodationRequest.objects.filter(id=linked_request_id).update(
            status=AccommodationRequestStatus.ALLOCATED.value,
            decided_by_user_id=allotted_by_user_id,
            decided_at=timezone.now(),
        )

    emit_notification(
        recipient_user_id=student_user_id,
        title="Hostel Room Allotted",
        message=f"Allotted Room {room.room_number} (Bed {allotment.bed_number}).",
        event_type=NotificationEventType.ALLOTMENT_UPDATED,
        link="/hostel/occupancy",
    )

    return allotment


@transaction.atomic
def vacate_room(
    allotment_id: int,
    vacated_date: date | None = None,
    vacation_clearance_status: bool = True,
    vacation_remarks: str = "",
    actor_user_id: int | None = None,
) -> RoomAllotment:
    """CFR-HM-004, HM-UC-007: Record formal room vacation and release occupancy."""
    allotment = (
        RoomAllotment.objects.select_for_update()
        .select_related("room")
        .get(id=allotment_id, status=AllotmentStatus.ACTIVE.value)
    )
    room = Room.objects.select_for_update().get(id=allotment.room_id)

    allotment.status = AllotmentStatus.VACATED.value
    allotment.vacated_date = vacated_date or timezone.now().date()
    allotment.vacation_clearance_status = vacation_clearance_status
    allotment.vacation_remarks = vacation_remarks.strip()
    allotment.save(
        update_fields=[
            "status",
            "vacated_date",
            "vacation_clearance_status",
            "vacation_remarks",
            "updated_at",
        ]
    )

    # Decrement room occupancy safely
    if room.current_occupancy > 0:
        room.current_occupancy -= 1

    if room.current_occupancy == 0:
        room.status = RoomStatus.AVAILABLE.value
    elif room.current_occupancy < room.capacity:
        room.status = RoomStatus.OCCUPIED.value
    room.save(update_fields=["current_occupancy", "status", "updated_at"])

    emit_notification(
        recipient_user_id=allotment.student_user_id,
        title="Hostel Room Vacated",
        message=f"Formal vacation recorded for Room {room.room_number} in {room.hostel.code}.",
        event_type=NotificationEventType.ROOM_VACATED,
    )

    return allotment
