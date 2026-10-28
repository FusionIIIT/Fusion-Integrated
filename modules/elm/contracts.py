"""elm's public surface. Plural by signature."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from modules.elm.models import LeaveRequest


@dataclass(frozen=True)
class LeaveRequestDTO:
    """Data transfer object for leave request details."""
    user_id: int
    status: str
    start_date: str
    end_date: str


def get_leave_request_status(user_ids: Sequence[int],
                             leave_year: str) -> dict[int, LeaveRequestDTO]:
    """Retrieve the status of leave requests for a list of users in a given year."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    rows = (LeaveRequest.objects
            .filter(user_id__in=ids, year=leave_year)
            .values_list("user_id", "status", "start_date", "end_date"))
    return {uid: LeaveRequestDTO(uid, status, start_date, end_date)
            for uid, status, start_date, end_date in rows}
