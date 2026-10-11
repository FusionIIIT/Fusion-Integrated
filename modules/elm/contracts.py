from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from modules.elm.models import Leave


@dataclass(frozen=True)
class LeaveBalanceDTO:
    user_id: int
    leave_type: str
    days: int


def get_leave_balances(user_ids: Sequence[int]) -> dict[int, LeaveBalanceDTO]:
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    rows = (Leave.objects
            .filter(user_id__in=ids)
            .values_list("user_id", "leave_type", "days", flat=True))
    balances: dict[int, dict[str, int]] = {}
    for uid, leave_type, days in rows:
        balances.setdefault(uid, {})[leave_type] = days
    return {uid: LeaveBalanceDTO(uid, leave_type, days)
            for uid, leave_type_days in balances.items()}
