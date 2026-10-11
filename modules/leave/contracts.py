"""leave's public surface. Plural by signature."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from modules.leave.models import LeaveApplication, LeaveBalance


@dataclass(frozen=True)
class LeaveBalanceDTO:
    user_id: int
    year: str
    available: dict[str, Decimal] = field(default_factory=dict)


def get_leave_balances(user_ids: Sequence[int],
                       year: str) -> dict[int, LeaveBalanceDTO]:
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    out = {uid: {} for uid in ids}
    for row in LeaveBalance.objects.filter(user_id__in=ids, year=year):
        out[row.user_id][row.leave_type] = row.available
    return {uid: LeaveBalanceDTO(uid, year, avail) for uid, avail in out.items()}


def get_absences(user_ids: Sequence[int], on_date: date) -> dict[int, bool]:
    """Who is on approved leave on a given date — for whoever needs to know
    that an approver is away."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    away = set(LeaveApplication.objects
               .filter(user_id__in=ids, status="approved", kind="leave",
                       start_date__lte=on_date, end_date__gte=on_date)
               .values_list("user_id", flat=True))
    return {uid: uid in away for uid in ids}
