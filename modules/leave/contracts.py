"""Leave module public contract surface.

All cross-module getters MUST take a sequence of ids to prevent N+1 queries.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from modules.leave.models import LeaveRequest


@dataclass(frozen=True)
class LeaveStatusDTO:
    user_id: int
    has_active_leave: bool
    active_leave_count: int
    is_currently_on_leave: bool


def get_leave_statuses(user_ids: Sequence[int], target_date: date | None = None) -> dict[int, LeaveStatusDTO]:
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    today = target_date or date.today()

    active_requests = list(
        LeaveRequest.objects.filter(user_id__in=ids, status__in=["pending", "approved"])
        .values("user_id", "status", "start_date", "end_date")
    )

    counts: dict[int, int] = {}
    on_leave_today: set[int] = set()

    for req in active_requests:
        uid = req["user_id"]
        counts[uid] = counts.get(uid, 0) + 1
        if req["status"] == "approved" and req["start_date"] <= today <= req["end_date"]:
            on_leave_today.add(uid)

    return {
        uid: LeaveStatusDTO(
            user_id=uid,
            has_active_leave=counts.get(uid, 0) > 0,
            active_leave_count=counts.get(uid, 0),
            is_currently_on_leave=uid in on_leave_today,
        )
        for uid in ids
    }
