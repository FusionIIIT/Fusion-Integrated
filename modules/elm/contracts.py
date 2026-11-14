"""elm's public surface. Plural by signature."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from modules.elm.domain import state_machine as sm
from modules.elm.models import LeaveRequest


def get_on_leave(user_ids: Sequence[int], on: date) -> dict[int, bool]:
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    away = set(LeaveRequest.objects
               .filter(user_id__in=ids, status__in=(sm.APPROVED, sm.CANCELLATION_PENDING),
                       start_date__lte=on, end_date__gte=on)
               .values_list("user_id", flat=True))
    return {uid: uid in away for uid in ids}
