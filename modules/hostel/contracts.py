"""Public contract for the Hostel Management module (ADR-0010).

Other modules may import ONLY this file from modules.hostel.
"""

from __future__ import annotations

from typing import Sequence
from modules.hostel.domain.enums import AllotmentStatus
from modules.hostel.models import Hostel, RoomAllotment


def is_student_hosteler(student_user_id: int) -> bool:
    """Returns True if student has an active room allotment in any hostel."""
    return RoomAllotment.objects.filter(
        student_user_id=student_user_id, status=AllotmentStatus.ACTIVE.value
    ).exists()


def get_student_hostel_allocations(
    student_user_ids: Sequence[int],
) -> dict[int, dict]:
    """Returns active hostel and room information for given students.
    Plural signature to prevent N+1 queries across module boundaries.
    """
    rows = (
        RoomAllotment.objects.filter(
            student_user_id__in=student_user_ids,
            status=AllotmentStatus.ACTIVE.value,
        )
        .select_related("hostel", "room")
    )
    result = {}
    for r in rows:
        result[r.student_user_id] = {
            "hostel_id": r.hostel_id,
            "hostel_name": r.hostel.name,
            "hostel_code": r.hostel.code,
            "room_id": r.room_id,
            "room_number": r.room.room_number,
            "allotted_at": r.allotted_at.isoformat() if r.allotted_at else None,
        }
    return result


def get_hostel_summaries(hostel_ids: Sequence[int] | None = None) -> list[dict]:
    """Returns basic capacity and active status for hostels."""
    qs = Hostel.objects.all()
    if hostel_ids is not None:
        qs = qs.filter(id__in=hostel_ids)
    return [
        {
            "id": h.id,
            "code": h.code,
            "name": h.name,
            "gender_type": h.gender_type,
            "is_active": h.is_active,
            "capacity": h.capacity,
        }
        for h in qs
    ]
