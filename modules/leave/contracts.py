"""leave's public surface. Plural by signature."""
from __future__ import annotations

import datetime
from collections.abc import Sequence
from dataclasses import dataclass

from modules.leave.models import LeaveBalance


@dataclass(frozen=True)
class LeaveBalanceDTO:
    user_id: int
    category: str
    year: int
    allocated: float
    used: float
    pending: float
    available: float


def get_leave_balances(user_ids: Sequence[int]) -> dict[int, list[LeaveBalanceDTO]]:
    """Return active year leave balances for the requested user IDs."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    current_year = datetime.date.today().year
    records = LeaveBalance.objects.filter(user_id__in=ids, year=current_year)

    result: dict[int, list[LeaveBalanceDTO]] = {uid: [] for uid in ids}
    for b in records:
        result[b.user_id].append(
            LeaveBalanceDTO(
                user_id=b.user_id,
                category=b.category,
                year=b.year,
                allocated=b.allocated,
                used=b.used,
                pending=b.pending,
                available=b.available,
            )
        )
    return result
