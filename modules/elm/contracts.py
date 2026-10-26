"""Public contract for Employee Leave Management (ADR-0013).

The ONLY interface other modules may import from ELM.
All getters are plural by signature.
"""

from __future__ import annotations

import datetime
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from modules.elm.models import LeaveApplication, LeaveBalance


@dataclass(frozen=True)
class ActiveLeaveDTO:
    user_id: int
    leave_category: str
    start_date: datetime.date
    end_date: datetime.date
    status: str
    half_day: bool = False
    half_day_type: str = ""


@dataclass(frozen=True)
class LeaveBalanceDTO:
    user_id: int
    year: int
    leave_category: str
    credited: Decimal
    used: Decimal
    available: Decimal


def get_active_leaves_for_users(
    user_ids: Sequence[int],
    on_date: datetime.date | None = None,
) -> dict[int, list[ActiveLeaveDTO]]:
    """Return active leaves for the specified users."""
    ids = [int(i) for i in user_ids if i is not None]
    if not ids:
        return {}

    qs = LeaveApplication.objects.filter(user_id__in=ids, status="approved")
    if on_date is not None:
        qs = qs.filter(start_date__lte=on_date, end_date__gte=on_date)

    result: dict[int, list[ActiveLeaveDTO]] = {uid: [] for uid in ids}
    for row in qs:
        result[row.user_id].append(
            ActiveLeaveDTO(
                user_id=row.user_id,
                leave_category=row.leave_category,
                start_date=row.start_date,
                end_date=row.end_date,
                status=row.status,
                half_day=row.half_day,
                half_day_type=row.half_day_type,
            )
        )
    return result


def get_leave_balances_for_users(
    user_ids: Sequence[int],
    year: int = 2026,
) -> dict[int, list[LeaveBalanceDTO]]:
    """Return leave balances for the specified users in a given year."""
    ids = [int(i) for i in user_ids if i is not None]
    if not ids:
        return {}

    qs = LeaveBalance.objects.filter(user_id__in=ids, year=year)
    result: dict[int, list[LeaveBalanceDTO]] = {uid: [] for uid in ids}
    for row in qs:
        result[row.user_id].append(
            LeaveBalanceDTO(
                user_id=row.user_id,
                year=row.year,
                leave_category=row.leave_category,
                credited=row.credited,
                used=row.used,
                available=row.available,
            )
        )
    return result
