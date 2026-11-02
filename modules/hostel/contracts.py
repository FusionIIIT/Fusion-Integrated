"""Hostel Management public contract for other Fusion modules."""

from datetime import date
from typing import Any

from .models import Hostel, LeaveRequest, RoomAllotment


def get_student_hostel_allocation(student_user_id: int) -> dict[str, Any] | None:
    """Return active room allotment for a student, if any."""
    allotment = (
        RoomAllotment.objects.filter(student_user_id=student_user_id, is_active=True)
        .select_related("room", "hostel")
        .first()
    )
    if not allotment:
        return None
    return {
        "allotment_id": allotment.id,
        "hostel_id": allotment.hostel_id,
        "hostel_name": allotment.hostel.name,
        "hostel_code": allotment.hostel.code,
        "room_id": allotment.room_id,
        "room_number": allotment.room.room_number,
        "allotted_at": allotment.allotted_at.isoformat(),
    }


def is_student_resident_in_hostel(student_user_id: int, hostel_id: int) -> bool:
    """Check if student has an active room in the specified hostel."""
    return RoomAllotment.objects.filter(
        student_user_id=student_user_id, hostel_id=hostel_id, is_active=True
    ).exists()


def get_student_leave_status(student_user_id: int, check_date: date) -> str | None:
    """Check if student is on approved leave on a given date."""
    leave = LeaveRequest.objects.filter(
        student_user_id=student_user_id,
        status="approved",
        start_date__lte=check_date,
        end_date__gte=check_date,
    ).first()
    return leave.leave_type if leave else None


def get_hostel_details(hostel_id: int) -> dict[str, Any] | None:
    """Return hostel master info."""
    hostel = Hostel.objects.filter(id=hostel_id).first()
    if not hostel:
        return None
    return {
        "id": hostel.id,
        "name": hostel.name,
        "code": hostel.code,
        "gender_policy": hostel.gender_policy,
        "capacity": hostel.capacity,
        "is_active": hostel.is_active,
    }
