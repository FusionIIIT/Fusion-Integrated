"""Public ELM read contract for other modules. Cross-module lookups are plural."""
from collections.abc import Sequence
from dataclasses import dataclass
from modules.elm.models import LeaveRequest

@dataclass(frozen=True)
class LeaveStatusDTO:
    user_id: int
    approved_request_count: int


def get_approved_leave_counts(user_ids: Sequence[int]) -> dict[int, LeaveStatusDTO]:
    ids = {int(uid) for uid in user_ids if uid is not None}
    counts = {}
    for uid in LeaveRequest.objects.filter(user_id__in=ids, status="approved").values_list("user_id", flat=True):
        counts[uid] = counts.get(uid, 0) + 1
    return {uid: LeaveStatusDTO(uid, counts.get(uid, 0)) for uid in ids}
