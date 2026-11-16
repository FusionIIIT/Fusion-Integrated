"""Contracts for Hostel Management module.

Every getter is plural: takes a Sequence of IDs.
"""

from collections.abc import Sequence
from typing import Any

from modules.hostel.models import Hostel, RoomAllotment


def get_student_hostel_allocations(user_ids: Sequence[int]) -> Sequence[dict[str, Any]]:
    allotments = RoomAllotment.objects.filter(
        user_id__in=user_ids, is_active=True
    ).select_related("room", "room__hostel")

    return [
        {
            "user_id": a.user_id,
            "hostel_name": a.room.hostel.name,
            "hostel_code": a.room.hostel.code,
            "room_number": a.room.room_number,
            "academic_year": a.academic_year,
        }
        for a in allotments
    ]


def get_hostel_summaries(hostel_ids: Sequence[int]) -> Sequence[dict[str, Any]]:
    hostels = Hostel.objects.filter(id__in=hostel_ids)
    return [
        {
            "id": h.id,
            "name": h.name,
            "code": h.code,
            "is_active": h.is_active,
            "total_rooms": h.rooms.count(),
        }
        for h in hostels
    ]
