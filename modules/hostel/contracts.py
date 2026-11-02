"""Hostel Management public contract surface. Plural by signature."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from modules.hostel.models import HostelFine, HostelLeave, RoomAllotment


@dataclass(frozen=True)
class HostelAllocationDTO:
    user_id: int
    has_active_hostel: bool
    hostel_code: str | None
    room_number: str | None
    bed_number: str | None


@dataclass(frozen=True)
class HostelNoDuesDTO:
    user_id: int
    cleared: bool
    pending_fines_count: int
    total_fine_amount: float
    blocking_reasons: tuple[str, ...]


@dataclass(frozen=True)
class StudentLeaveSummaryDTO:
    user_id: int
    active_leave: bool
    total_leaves_taken: int


def get_student_hostel_allocations(
    user_ids: Sequence[int],
) -> dict[int, HostelAllocationDTO]:
    """Return current active hostel and room for given student user IDs."""
    ids = {int(uid) for uid in user_ids if uid is not None}
    if not ids:
        return {}

    allotments = RoomAllotment.objects.filter(
        student_user_id__in=ids, status="active"
    ).select_related("hostel", "room")
    result = {
        uid: HostelAllocationDTO(
            user_id=uid,
            has_active_hostel=False,
            hostel_code=None,
            room_number=None,
            bed_number=None,
        )
        for uid in ids
    }
    for alt in allotments:
        result[alt.student_user_id] = HostelAllocationDTO(
            user_id=alt.student_user_id,
            has_active_hostel=True,
            hostel_code=alt.hostel.code,
            room_number=alt.room.room_number,
            bed_number=alt.bed_number,
        )
    return result


def get_hostel_no_dues_clearances(
    user_ids: Sequence[int],
) -> dict[int, HostelNoDuesDTO]:
    """Verify if student has cleared all hostel dues and fines."""
    ids = {int(uid) for uid in user_ids if uid is not None}
    if not ids:
        return {}

    pending_fines = HostelFine.objects.filter(student_user_id__in=ids, status="pending")
    result = {}
    for uid in ids:
        user_fines = [f for f in pending_fines if f.student_user_id == uid]
        total_amount = sum(float(f.amount) for f in user_fines)
        reasons = tuple(f"Fine #{f.id}: {f.reason} (Rs. {f.amount})" for f in user_fines)
        result[uid] = HostelNoDuesDTO(
            user_id=uid,
            cleared=(len(user_fines) == 0),
            pending_fines_count=len(user_fines),
            total_fine_amount=total_amount,
            blocking_reasons=reasons,
        )
    return result


def get_student_leave_summaries(
    user_ids: Sequence[int],
) -> dict[int, StudentLeaveSummaryDTO]:
    """Summarize hostel leaves for given students."""
    ids = {int(uid) for uid in user_ids if uid is not None}
    if not ids:
        return {}

    leaves = HostelLeave.objects.filter(student_user_id__in=ids)
    result = {}
    for uid in ids:
        user_leaves = [item for item in leaves if item.student_user_id == uid]
        active = any(item.status == "approved" for item in user_leaves)
        result[uid] = StudentLeaveSummaryDTO(
            user_id=uid,
            active_leave=active,
            total_leaves_taken=len(user_leaves),
        )
    return result
