"""leave's public surface. Plural by signature."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class LeaveBalanceDTO:
    user_id: int
    category: str
    balance: float


def get_leave_balances(user_ids: Sequence[int]) -> dict[int, list[LeaveBalanceDTO]]:
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    return {uid: [] for uid in ids}
