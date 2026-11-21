"""Room management and Caretaker individual room exchange (3.1 & 3.2, CFR-HM-006, BR-HM-010)."""

from django.db import transaction
from ..domain.errors import (
    HostelDomainError,
    InactiveHostelError,
    RoomCapacityExceededError,
)
from ..models import Hostel, Room, RoomAllotment, RoomAssignmentHistory
from .notification_service import create_notification


@transaction.atomic
def create_room(
    hostel_id: int,
    room_number: str,
    floor: int = 1,
    capacity: int = 2,
    room_type: str = "double",
) -> Room:
    hostel = Hostel.objects.filter(id=hostel_id).first()
    if not hostel:
        raise HostelDomainError(f"Hostel {hostel_id} not found.", code="not_found")
    if Room.objects.filter(hostel=hostel, room_number=room_number.strip()).exists():
        raise HostelDomainError(f"Room {room_number} already exists in {hostel.name}.", code="duplicate_room")

    return Room.objects.create(
        hostel=hostel,
        room_number=room_number.strip(),
        floor=floor,
        capacity=capacity,
        current_occupancy=0,
        room_type=room_type,
        is_available=True,
    )


@transaction.atomic
def update_room(
    room_id: int,
    capacity: int | None = None,
    is_available: bool | None = None,
    room_type: str | None = None,
) -> Room:
    room = Room.objects.select_for_update().filter(id=room_id).first()
    if not room:
        raise HostelDomainError(f"Room {room_id} not found.", code="not_found")

    if capacity is not None:
        if room.current_occupancy > capacity:
            raise RoomCapacityExceededError(room.room_number, capacity, room.current_occupancy)
        room.capacity = capacity
    if is_available is not None:
        room.is_available = is_available
    if room_type is not None:
        room.room_type = room_type

    room.save()
    return room


@transaction.atomic
def record_individual_room_exchange(
    caretaker_user_id: int,
    hostel_id: int,
    student_user_id_1: int,
    target_room_id: int,
    student_user_id_2: int | None = None,
    reason: str = "",
) -> tuple[RoomAllotment, RoomAllotment | None]:
    """Caretaker records individual room exchange within assigned hostel (HM-UC-010, BR-HM-010).

    Can be:
    1. Single student moving to an available room (student_user_id_2 is None).
    2. Mutual swap between student 1 and student 2.
    """
    hostel = Hostel.objects.filter(id=hostel_id).first()
    if not hostel:
        raise HostelDomainError(f"Hostel {hostel_id} not found.", code="not_found")
    if not hostel.is_active:
        raise InactiveHostelError(hostel.name)

    allotment_1 = (
        RoomAllotment.objects.select_for_update()
        .filter(student_user_id=student_user_id_1, hostel=hostel, is_active=True)
        .first()
    )
    if not allotment_1:
        raise HostelDomainError(f"Student {student_user_id_1} has no active allotment in {hostel.name}.")

    current_room_1 = Room.objects.select_for_update().get(id=allotment_1.room_id)
    target_room = Room.objects.select_for_update().filter(id=target_room_id, hostel=hostel).first()
    if not target_room:
        raise HostelDomainError(f"Target room {target_room_id} not found in {hostel.name}.")

    allotment_2 = None
    if student_user_id_2:
        # Mutual swap
        allotment_2 = (
            RoomAllotment.objects.select_for_update()
            .filter(student_user_id=student_user_id_2, hostel=hostel, is_active=True)
            .first()
        )
        if not allotment_2:
            raise HostelDomainError(f"Student {student_user_id_2} has no active allotment in {hostel.name}.")

        if allotment_2.room_id != target_room.id:
            raise HostelDomainError(f"Student {student_user_id_2} is not in target room {target_room.room_number}.")

        # Perform mutual swap
        allotment_1.room = target_room
        allotment_1.save()

        allotment_2.room = current_room_1
        allotment_2.save()

        # Audit history (BR-HM-009)
        RoomAssignmentHistory.objects.create(
            student_user_id=student_user_id_1,
            student_roll_number=allotment_1.student_roll_number,
            from_room=current_room_1,
            to_room=target_room,
            action_type="exchange",
            performed_by_user_id=caretaker_user_id,
            reason=f"Mutual exchange with {allotment_2.student_roll_number}. {reason}".strip(),
        )
        RoomAssignmentHistory.objects.create(
            student_user_id=student_user_id_2,
            student_roll_number=allotment_2.student_roll_number,
            from_room=target_room,
            to_room=current_room_1,
            action_type="exchange",
            performed_by_user_id=caretaker_user_id,
            reason=f"Mutual exchange with {allotment_1.student_roll_number}. {reason}".strip(),
        )

        create_notification(
            recipient_user_id=student_user_id_1,
            event_type="room_exchange",
            title="Room Exchanged",
            message=f"You have been moved to room {target_room.room_number} in {hostel.name}.",
            reference_id=str(allotment_1.id),
        )
        create_notification(
            recipient_user_id=student_user_id_2,
            event_type="room_exchange",
            title="Room Exchanged",
            message=f"You have been moved to room {current_room_1.room_number} in {hostel.name}.",
            reference_id=str(allotment_2.id),
        )
        return allotment_1, allotment_2

    else:
        # Move to empty/available slot
        if target_room.current_occupancy + 1 > target_room.capacity:
            raise RoomCapacityExceededError(target_room.room_number, target_room.capacity, target_room.current_occupancy)

        # Decrement old room, increment new room
        current_room_1.current_occupancy = max(0, current_room_1.current_occupancy - 1)
        current_room_1.save()

        target_room.current_occupancy += 1
        target_room.save()

        allotment_1.room = target_room
        allotment_1.save()

        RoomAssignmentHistory.objects.create(
            student_user_id=student_user_id_1,
            student_roll_number=allotment_1.student_roll_number,
            from_room=current_room_1,
            to_room=target_room,
            action_type="transfer",
            performed_by_user_id=caretaker_user_id,
            reason=reason.strip(),
        )

        create_notification(
            recipient_user_id=student_user_id_1,
            event_type="room_exchange",
            title="Room Changed",
            message=f"Your room has been changed to {target_room.room_number} in {hostel.name}.",
            reference_id=str(allotment_1.id),
        )
        return allotment_1, None
