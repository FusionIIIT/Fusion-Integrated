"""leave's public surface. Plural by signature.

Other modules ask whether someone is away; nobody asks for one person at a
time — a timetabler checks a panel.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from django.db.models.functions import Coalesce

from modules.leave.domain.states import APPROVED


@dataclass(frozen=True)
class LeaveStatusDTO:
    user_id: int
    on_leave: bool
    until: date | None
    categories: tuple[str, ...]
    request_ids: tuple[int, ...]


def get_leave_status(user_ids: Sequence[int],
                     on_date: date) -> dict[int, LeaveStatusDTO]:
    """Who is away on `on_date`: approved leave spanning that date, using
    the actual return date where a resumption review recorded one.

    A missing user is absent from the mapping — the same visible, testable
    case directory exposes, rather than a silent default.
    """
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    from modules.leave.models import LeaveRequest

    rows = (LeaveRequest.objects
            .filter(user_id__in=ids, status=APPROVED,
                    start_date__lte=on_date)
            .annotate(effective_end=Coalesce("actual_end_date", "end_date"))
            .filter(effective_end__gte=on_date)
            .order_by("start_date"))

    found: dict[int, tuple[set[str], date, list[int]]] = {}
    for row in rows:
        categories, until, req_ids = found.get(
            row.user_id, (set(), on_date, []))
        categories.add(row.category)
        until = max(until, row.effective_end)
        req_ids.append(row.id)
        found[row.user_id] = (categories, until, req_ids)

    return {
        uid: LeaveStatusDTO(
            user_id=uid,
            on_leave=uid in found,
            until=found[uid][1] if uid in found else None,
            categories=tuple(sorted(found[uid][0])) if uid in found else (),
            request_ids=tuple(found[uid][2]) if uid in found else (),
        )
        for uid in ids
    }


def on_leave_ids(user_ids: Sequence[int], on_date: date) -> set[int]:
    """The filter everyone actually wants: which of these people are away."""
    return {uid for uid, dto in get_leave_status(user_ids, on_date).items()
            if dto.on_leave}
