"""leave's public surface. The ONLY thing other modules may import.

Plural by signature on purpose — a singular getter is what gets called inside a
loop, and making the batched form the only form available means an N+1 here is
unwritable rather than merely discouraged.

Nothing here mutates. If another module needs a change made, that is an event,
not a function call.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from modules.leave.models import LeaveRequest


@dataclass(frozen=True)
class LeaveSummaryDTO:
    user_id: int
    #: Leave in effect or approved and not yet started.
    on_leave: bool
    #: Anything still moving through the hierarchy.
    pending: int
    #: Categories the employee is currently on leave for.
    categories: tuple[str, ...]


def get_leave_summaries(user_ids: Sequence[int]) -> dict[int, LeaveSummaryDTO]:
    """Who is on leave, and what is still pending, for a batch of people.

    A no-dues desk asking about one student is the case this exists for: it
    needs a yes/no plus the reason, not a leave request list.
    """
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    rows = (LeaveRequest.objects
            .filter(user_id__in=ids, kind="new")
            .exclude(status__in=["rejected", "withdrawn", "cancelled"])
            .values("user_id", "category", "status"))

    out: dict[int, LeaveSummaryDTO] = {
        uid: LeaveSummaryDTO(uid, on_leave=False, pending=0, categories=())
        for uid in ids}
    seen: dict[int, set[str]] = {uid: set() for uid in ids}
    for row in rows:
        uid = row["user_id"]
        approved = row["status"] == "approved"
        seen[uid].add(row["category"])
        out[uid] = LeaveSummaryDTO(
            uid,
            on_leave=approved or out[uid].on_leave,
            pending=out[uid].pending + (0 if approved else 1),
            categories=tuple(sorted(seen[uid])))
    return out


def get_on_leave_user_ids(user_ids: Sequence[int]) -> list[int]:
    """The subset currently on leave, for whoever needs to exclude them from a
    duty roster."""
    return sorted(uid for uid, s in get_leave_summaries(user_ids).items()
                  if s.on_leave)
