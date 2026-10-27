"""Leave module public contract surface (ADR-0013)."""
from __future__ import annotations

import datetime
from collections.abc import Sequence
from dataclasses import dataclass

from modules.leave.models import LeaveApplication


@dataclass(frozen=True)
class LeaveStatusDTO:
    user_id: int
    is_on_leave: bool
    category: str | None
    end_date: datetime.date | None


def get_leave_status(
    user_ids: Sequence[int],
    on_date: datetime.date | None = None,
) -> dict[int, LeaveStatusDTO]:
    """Query whether users are currently on approved leave on the given date."""
    if on_date is None:
        on_date = datetime.date.today()

    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    apps = LeaveApplication.objects.filter(
        user_id__in=ids,
        status="approved",
        start_date__lte=on_date,
        end_date__gte=on_date,
    )

    on_leave_map = {app.user_id: app for app in apps}

    result = {}
    for uid in ids:
        app = on_leave_map.get(uid)
        if app:
            result[uid] = LeaveStatusDTO(
                user_id=uid,
                is_on_leave=True,
                category=app.category,
                end_date=app.end_date,
            )
        else:
            result[uid] = LeaveStatusDTO(
                user_id=uid,
                is_on_leave=False,
                category=None,
                end_date=None,
            )
    return result
