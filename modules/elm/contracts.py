"""elm's public surface. Plural by signature.

Another module asks "is this person on leave?" without reaching into ELM's
tables; the answer is a DTO, and ELM's schema stays its own business.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from django.utils import timezone


@dataclass(frozen=True)
class ActiveLeaveDTO:
    user_id: int
    on_leave: bool
    category: str
    until: date | None


def get_active_leave(user_ids: Sequence[int], *,
                     on_date: date | None = None) -> dict[int, ActiveLeaveDTO]:
    """Whether each employee is on approved leave, as of `on_date`.

    A single dated question rather than a stream, so a caller checking a whole
    unit makes one call, not one per person.
    """
    from modules.elm.models import LeaveRequest

    ids = {int(i) for i in user_ids if i is not None}
    day = on_date or timezone.localdate()
    if not ids:
        return {}
    rows = (LeaveRequest.objects
            .filter(user_id__in=ids, kind="new", status="approved",
                    start_date__lte=day, end_date__gte=day)
            .values_list("user_id", "category", "end_date"))
    found = {uid: (category, end) for uid, category, end in rows}
    return {
        uid: ActiveLeaveDTO(uid, uid in found,
                            found.get(uid, ("", None))[0],
                            found.get(uid, ("", None))[1])
        for uid in ids
    }
