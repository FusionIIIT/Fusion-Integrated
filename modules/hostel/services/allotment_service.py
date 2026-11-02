"""Accommodation request and batch room allotment services (3.1 & 3.2, CFR-HM-003, CFR-HM-004, BW-HM-01)."""

from django.db import transaction
from django.utils import timezone
from ..domain.constants import AccommodationStatus
from ..domain.errors import (
    DuplicateActiveAllotmentError,
    HostelDomainError,
    InactiveHostelError,
    RoomCapacityExceededError,
)
from ..domain.state_machine import WorkflowStateMachine
from ..models import (
    AccommodationRequest,
    Hostel,
    Room,
    RoomAllotment,
    RoomAssignmentHistory,
)
from .notification_service import create_notification


@transaction.atomic
def submit_accommodation_request(
    student_user_id: int,
    student_roll_number: str,
    student_name: str,
    academic_year: str,
    semester: str,
    requested_hostel_id: int | None = None,
    reason: str = "",
) -> AccommodationRequest:
    """Student submits hostel accommodation request (HM-UC-005, BW-HM-01)."""
    # Check if student already has active allotment
    if RoomAllotment.objects.filter(student_user_id=student_user_id, is_active=True).exists():
        raise DuplicateActiveAllotmentError(student_user_id)

    # Check if student already has a pending submitted request
    pending = AccommodationRequest.objects.filter(
        student_user_id=student_user_id,
        status=AccommodationStatus.SUBMITTED.value,
    ).first()
    if pending:
        return pending

    req = AccommodationRequest.objects.create(
        student_user_id=student_user_id,
        student_roll_number=student_roll_number.strip(),
        student_name=student_name.strip(),
        academic_year=academic_year.strip(),
        semester=semester.strip(),
        requested_hostel_id=requested_hostel_id,
        reason=reason.strip(),
        status=AccommodationStatus.SUBMITTED.value,
    )

    create_notification(
        recipient_user_id=student_user_id,
        event_type="accommodation_request_submitted",
        title="Accommodation Request Submitted",
        message="Your hostel accommodation request has been submitted for batch allotment.",
        reference_id=str(req.id),
    )
    return req


@transaction.atomic
def record_allotment_decision(
    super_admin_user_id: int,
    request_id: int,
    room_id: int,
    allotment_reason: str = "Batch allotment round",
) -> RoomAllotment:
    """Super Admin records allotment decision for request (HM-UC-006, BW-HM-01, BR-HM-010)."""
    req = AccommodationRequest.objects.select_for_update().filter(id=request_id).first()
    if not req:
        raise HostelDomainError(f"Accommodation request {request_id} not found.", code="not_found")

    WorkflowStateMachine.validate_accommodation_transition(
        req.status, AccommodationStatus.ALLOTTED.value
    )

    room = Room.objects.select_for_update().select_related("hostel").filter(id=room_id).first()
    if not room:
        raise HostelDomainError(f"Room {room_id} not found.", code="not_found")
    if not room.hostel.is_active:
        raise InactiveHostelError(room.hostel.name)

    # Check capacity limit (BR-HM-010)
    if room.current_occupancy + 1 > room.capacity:
        raise RoomCapacityExceededError(room.room_number, room.capacity, room.current_occupancy)

    # Check no duplicate active allotment
    if RoomAllotment.objects.filter(student_user_id=req.student_user_id, is_active=True).exists():
        raise DuplicateActiveAllotmentError(req.student_user_id)

    # Increment room occupancy
    room.current_occupancy += 1
    room.save(update_fields=["current_occupancy", "updated_at"])

    # Create Allotment
    allotment = RoomAllotment.objects.create(
        room=room,
        hostel=room.hostel,
        student_user_id=req.student_user_id,
        student_roll_number=req.student_roll_number,
        student_name=req.student_name,
        allotted_by_user_id=super_admin_user_id,
        is_active=True,
    )

    # Update request status
    req.status = AccommodationStatus.ALLOTTED.value
    req.save(update_fields=["status", "updated_at"])

    # Audit History (BR-HM-009)
    RoomAssignmentHistory.objects.create(
        student_user_id=req.student_user_id,
        student_roll_number=req.student_roll_number,
        from_room=None,
        to_room=room,
        action_type="allotment",
        performed_by_user_id=super_admin_user_id,
        reason=allotment_reason,
    )

    create_notification(
        recipient_user_id=req.student_user_id,
        event_type="room_allotted",
        title="Hostel Room Allotted",
        message=f"You have been allotted Room {room.room_number} in {room.hostel.name}.",
        reference_id=str(allotment.id),
    )

    return allotment


@transaction.atomic
def record_reallotment(
    super_admin_user_id: int,
    allotment_id: int,
    new_room_id: int,
    reason: str = "Central re-allotment",
) -> RoomAllotment:
    """Super Admin central re-allotment (HM-UC-007, BR-HM-010)."""
    allotment = (
        RoomAllotment.objects.select_for_update()
        .select_related("room", "hostel")
        .filter(id=allotment_id, is_active=True)
        .first()
    )
    if not allotment:
        raise HostelDomainError(f"Active allotment {allotment_id} not found.", code="not_found")

    old_room = allotment.room
    new_room = Room.objects.select_for_update().select_related("hostel").filter(id=new_room_id).first()
    if not new_room:
        raise HostelDomainError(f"New room {new_room_id} not found.", code="not_found")
    if not new_room.hostel.is_active:
        raise InactiveHostelError(new_room.hostel.name)

    if new_room.current_occupancy + 1 > new_room.capacity:
        raise RoomCapacityExceededError(new_room.room_number, new_room.capacity, new_room.current_occupancy)

    # Update occupancies
    old_room.current_occupancy = max(0, old_room.current_occupancy - 1)
    old_room.save(update_fields=["current_occupancy", "updated_at"])

    new_room.current_occupancy += 1
    new_room.save(update_fields=["current_occupancy", "updated_at"])

    # Update allotment
    allotment.room = new_room
    allotment.hostel = new_room.hostel
    allotment.save(update_fields=["room", "hostel", "updated_at"])

    # Audit history (BR-HM-009)
    RoomAssignmentHistory.objects.create(
        student_user_id=allotment.student_user_id,
        student_roll_number=allotment.student_roll_number,
        from_room=old_room,
        to_room=new_room,
        action_type="re_allotment",
        performed_by_user_id=super_admin_user_id,
        reason=reason,
    )

    create_notification(
        recipient_user_id=allotment.student_user_id,
        event_type="room_reallotted",
        title="Room Re-allotted",
        message=f"Your room has been centrally re-allotted to Room {new_room.room_number} in {new_room.hostel.name}.",
        reference_id=str(allotment.id),
    )

    return allotment


@transaction.atomic
def record_room_vacation(
    super_admin_user_id: int,
    allotment_id: int,
    vacation_reason: str = "Semester completion / graduation",
) -> RoomAllotment:
    """Super Admin formal room-vacation update (HM-UC-007)."""
    allotment = (
        RoomAllotment.objects.select_for_update()
        .select_related("room", "hostel")
        .filter(id=allotment_id, is_active=True)
        .first()
    )
    if not allotment:
        raise HostelDomainError(f"Active allotment {allotment_id} not found.", code="not_found")

    room = allotment.room
    room.current_occupancy = max(0, room.current_occupancy - 1)
    room.save(update_fields=["current_occupancy", "updated_at"])

    allotment.is_active = False
    allotment.vacated_at = timezone.now()
    allotment.vacation_reason = vacation_reason
    allotment.save(update_fields=["is_active", "vacated_at", "vacation_reason", "updated_at"])

    # Audit history (BR-HM-009)
    RoomAssignmentHistory.objects.create(
        student_user_id=allotment.student_user_id,
        student_roll_number=allotment.student_roll_number,
        from_room=room,
        to_room=None,
        action_type="vacation",
        performed_by_user_id=super_admin_user_id,
        reason=vacation_reason,
    )

    create_notification(
        recipient_user_id=allotment.student_user_id,
        event_type="room_vacated",
        title="Hostel Room Vacated",
        message=f"Room {room.room_number} in {allotment.hostel.name} has been marked vacated.",
        reference_id=str(allotment.id),
    )

    return allotment
