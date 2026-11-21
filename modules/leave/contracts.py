"""leave's public surface. Plural by signature."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from modules.leave.domain.workflow import State
from modules.leave.models import LeaveRequest


@dataclass(frozen=True)
class LeaveStatusDTO:
    user_id: int
    on_leave: bool
    category: str = ""
    until: date | None = None


def get_leave_statuses(user_ids: Sequence[int], on: date) -> dict[int, LeaveStatusDTO]:
    """Who is on approved leave on a date, for attendance (BR-EL-028)."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    rows = (LeaveRequest.objects
            .filter(user_id__in=ids, status=State.APPROVED, start_date__lte=on,
                    end_date__gte=on, kind__in=(LeaveRequest.NEW, LeaveRequest.EXTENSION))
            .values_list("user_id", "category", "end_date"))
    found = {uid: LeaveStatusDTO(uid, True, cat, end) for uid, cat, end in rows}
    return {uid: found.get(uid, LeaveStatusDTO(uid, False)) for uid in ids}
