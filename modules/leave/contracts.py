"""Leave module public contract surface.

All cross-module getters MUST take a sequence of ids to prevent N+1 queries.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from modules.leave.models import LeaveRequest


@dataclass(frozen=True)
class LeaveStatusDTO:
    user_id: int
    has_active_leave: bool
    active_leave_count: int


def get_leave_statuses(user_ids: Sequence[int]) -> dict[int, LeaveStatusDTO]:
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    active_leaves = (
        LeaveRequest.objects.filter(user_id__in=ids, status__in=["pending", "approved"])
        .values_list("user_id", flat=True)
    )
    counts: dict[int, int] = {}
    for uid in active_leaves:
        counts[uid] = counts.get(uid, 0) + 1

    return {
        uid: LeaveStatusDTO(
            user_id=uid,
            has_active_leave=counts.get(uid, 0) > 0,
            active_leave_count=counts.get(uid, 0),
        )
        for uid in ids
    }
