"""leave's public surface. Plural by signature, like every other module's.

Leave affects things that are not leave: attendance expects to know who is
away, the academic office expects to know who is unreachable. Both ask once for
a list of people rather than once per person.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from modules.leave.domain import state_machine as sm
from modules.leave.models import LeaveRequest


@dataclass(frozen=True)
class LeaveStatusDTO:
    user_id: int
    on_leave: bool
    category: str = ""
    until: date | None = None


def get_leave_statuses(user_ids: Sequence[int], on_date: date
                       ) -> dict[int, LeaveStatusDTO]:
    """Who is on approved leave on a date, by IAM user id."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    rows = (LeaveRequest.objects
            .filter(user_id__in=ids, status=sm.APPROVED, kind="new",
                    start_date__lte=on_date, end_date__gte=on_date)
            .values_list("user_id", "category", "end_date"))
    found = {uid: LeaveStatusDTO(uid, True, category, until)
             for uid, category, until in rows}
    return {uid: found.get(uid, LeaveStatusDTO(uid, False)) for uid in ids}


def on_leave_user_ids(user_ids: Sequence[int], on_date: date) -> list[int]:
    """The subset of these people who are away. Plural, and one query."""
    return sorted(uid for uid, status_row
                  in get_leave_statuses(user_ids, on_date).items()
                  if status_row.on_leave)
