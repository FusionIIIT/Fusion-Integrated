"""Services for hostel accommodation and room allotment management.

All writes go through transactional choke points.
"""
from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError
from modules.hostel.domain.policies import PolicyViolationError, validate_room_capacity
from modules.hostel.models import AccommodationRequest, Hostel, Room, RoomAllotment, RoomExchange

# Declared permissions enforced in services and endpoints
PERM_ACCOMMODATION_CREATE = "hostel.accommodation.create"
PERM_ALLOTMENT_MANAGE = "hostel.allotment.manage"
PERM_ROOM_MANAGE = "hostel.room.manage"


@transaction.atomic
def submit_accommodation_request(
    user_id: int, preferred_hostel_id: int, academic_year: str, remarks: str = ""
) -> AccommodationRequest:
    if preferred_hostel_id:
        try:
            hostel = Hostel.objects.get(id=preferred_hostel_id, is_active=True)
        except Hostel.DoesNotExist as err:
            raise NotFoundError(
                "The requested hostel does not exist or is inactive.",
                code="hostel_not_found",
            ) from err
    else:
        hostel = None

    return AccommodationRequest.objects.create(
        user_id=user_id,
        preferred_hostel=hostel,
        academic_year=academic_year,
        remarks=remarks,
        status="SUBMITTED",
    )


@transaction.atomic
def allot_room(
    student_user_id: int, room_id: int, academic_year: str, allotted_by_user_id: int
) -> RoomAllotment:
    try:
        room = Room.objects.select_for_update().get(id=room_id)
    except Room.DoesNotExist as err:
        raise NotFoundError("The specified room does not exist.", code="room_not_found") from err

    active_count = RoomAllotment.objects.filter(room=room, is_active=True).count()
    try:
        validate_room_capacity(active_count, room.capacity)
    except PolicyViolationError as err:
        raise ConflictError(str(err), code="capacity_exceeded") from err

    # Deactivate existing active allotments for the student
    RoomAllotment.objects.filter(user_id=student_user_id, is_active=True).update(is_active=False)

    return RoomAllotment.objects.create(
        user_id=student_user_id,
        room=room,
        academic_year=academic_year,
        allotted_by_user_id=allotted_by_user_id,
        is_active=True,
    )


@transaction.atomic
def record_room_exchange(
    student_a_id: int, student_b_id: int, approved_by_user_id: int, reason: str
) -> RoomExchange:
    allot_a = (
        RoomAllotment.objects.select_for_update()
        .filter(user_id=student_a_id, is_active=True)
        .first()
    )
    allot_b = (
        RoomAllotment.objects.select_for_update()
        .filter(user_id=student_b_id, is_active=True)
        .first()
    )

    if not allot_a or not allot_b:
        raise NotFoundError(
            "Both students must have an active room allotment to exchange.",
            code="missing_allotment",
        )

    room_a = allot_a.room
    room_b = allot_b.room

    # Swap rooms
    allot_a.room = room_b
    allot_a.save()
    allot_b.room = room_a
    allot_b.save()

    return RoomExchange.objects.create(
        student_a_user_id=student_a_id,
        student_b_user_id=student_b_id,
        room_a=room_a,
        room_b=room_b,
        approved_by_user_id=approved_by_user_id,
        reason=reason,
    )
