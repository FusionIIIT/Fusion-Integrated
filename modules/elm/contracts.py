from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from modules.elm.models import Application


@dataclass(frozen=True)
class LeaveDTO:
    user_id: int
    category: str
    start_date: date
    end_date: date


def get_approved_leaves(user_ids: Sequence[int]) -> list[LeaveDTO]:
    return [LeaveDTO(r.user_id, r.category, r.start_date, r.effective_end_date)
            for r in Application.objects.filter(user_id__in=user_ids, kind="leave", status="approved")]
