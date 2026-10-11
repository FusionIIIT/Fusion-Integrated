"""leave's public surface. Plural by signature."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from modules.leave.models import LeaveApplication
from modules.leave.services import accounts


@dataclass(frozen=True)
class LeaveBalanceDTO:
    user_id: int
    year: int
    balances: dict[str, Decimal]


@dataclass(frozen=True)
class OnLeaveDTO:
    user_id: int
    on_leave: bool
    categories: tuple[str, ...]


def get_leave_balances(user_ids: Sequence[int], year: int) -> dict[int, LeaveBalanceDTO]:
    ids = {int(i) for i in user_ids if i is not None}
    return {uid: LeaveBalanceDTO(uid, year, accounts.balances(uid, year)) for uid in ids}


def get_on_leave(user_ids: Sequence[int], on: date) -> dict[int, OnLeaveDTO]:
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    rows = LeaveApplication.objects.filter(
        user_id__in=ids, status="approved",
        start_on__lte=on, end_on__gte=on,
    ).values_list("user_id", "category")
    grouped: dict[int, list[str]] = {uid: [] for uid in ids}
    for uid, cat in rows:
        grouped.setdefault(uid, []).append(cat)
    return {
        uid: OnLeaveDTO(uid, bool(cats), tuple(cats))
        for uid, cats in grouped.items()
    }
