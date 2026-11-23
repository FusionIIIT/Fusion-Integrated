"""Hostel Management public cross-module contracts surface.

Plural by signature and decoupled from internal representations.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from modules.hm.models import RoomAssignment


@dataclass(frozen=True)
class HostelAllocationDTO:
    user_id: int
    has_active_allocation: bool
    hostel_code: str | None
    room_number: str | None


def get_active_hostel_allocations(
    user_ids: Sequence[int],
) -> dict[int, HostelAllocationDTO]:
    """Retrieve active room assignments for given users across modules without FK leakage."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    active_assignments = (
        RoomAssignment.objects.filter(user_id__in=ids, status="active")
        .select_related("room__hostel")
        .all()
    )

    mapping: dict[int, RoomAssignment] = {a.user_id: a for a in active_assignments}
    results: dict[int, HostelAllocationDTO] = {}

    for uid in ids:
        assignment = mapping.get(uid)
        if assignment:
            results[uid] = HostelAllocationDTO(
                user_id=uid,
                has_active_allocation=True,
                hostel_code=assignment.room.hostel.code,
                room_number=assignment.room.room_number,
            )
        else:
            results[uid] = HostelAllocationDTO(
                user_id=uid,
                has_active_allocation=False,
                hostel_code=None,
                room_number=None,
            )

    return results
