"""elm's public surface. Plural by signature."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from modules.elm.domain import state_machine as sm
from modules.elm.models import LeaveRequest


@dataclass(frozen=True)
class OnLeaveDTO:
    user_id: int
    category: str
    start_date: date
    end_date: date


def get_approved_leaves(user_ids: Sequence[int], on: date) -> dict[int, OnLeaveDTO]:
    """Who is on approved leave on a date, for attendance (BR-EL-028)."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    rows = LeaveRequest.objects.filter(
        user_id__in=ids, state=sm.APPROVED, start_date__lte=on, end_date__gte=on,
        kind__in=(LeaveRequest.LEAVE, LeaveRequest.EXTENSION))
    return {r.user_id: OnLeaveDTO(r.user_id, r.category, r.start_date, r.end_date)
            for r in rows}
