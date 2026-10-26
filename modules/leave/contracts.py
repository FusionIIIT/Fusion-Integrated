"""Leave's public surface, plural by signature: approved leave as actually taken."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from django.db.models import Q

from modules.leave.models import LeaveRequest, Resumption


@dataclass(frozen=True)
class LeaveDayDTO:
    user_id: int
    category: str
    start: date
    end: date
    half: str
    request_id: int


def get_leave_days(user_ids: Sequence[int], start: date, end: date
                   ) -> dict[int, list[LeaveDayDTO]]:
    """Approved leave overlapping the window, cut short by a reviewed early return."""
    ids = {int(i) for i in user_ids if i is not None}
    out: dict[int, list[LeaveDayDTO]] = {i: [] for i in ids}
    if not ids:
        return out
    rows = list(LeaveRequest.objects
                .filter(user_id__in=ids, kind__in=("new", "extension"), status="approved")
                .filter(Q(start_date__lte=end) & Q(end_date__gte=start))
                .values_list("pk", "user_id", "category", "start_date", "end_date", "half",
                             "parent_id"))
    cut = dict(Resumption.objects.filter(
        leave_id__in={r[6] or r[0] for r in rows}, actual_end_date__isnull=False)
        .values_list("leave_id", "actual_end_date"))
    for pk, uid, category, s, e, half, parent_id in rows:
        actual = cut.get(parent_id or pk)
        if actual is not None:
            if actual < s:
                continue
            e = min(e, actual)
        out[uid].append(LeaveDayDTO(uid, category, max(s, start), min(e, end), half, pk))
    return out
