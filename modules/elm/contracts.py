"""ELM's public contract surface. Plural by signature (ADR-0013)."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from modules.elm.models import EmployeeLeaveBalance, LeaveApplication


@dataclass(frozen=True)
class LeaveBalanceDTO:
    user_id: int
    year: int
    leave_category: str
    available_days: Decimal
    allocated_days: Decimal
    availed_days: Decimal


@dataclass(frozen=True)
class ActiveLeaveDTO:
    user_id: int
    leave_id: int
    leave_category: str
    start_date: date
    end_date: date
    is_station_leave: bool
    status: str


def get_leave_balances(
    user_ids: Sequence[int],
    year: int | None = None,
) -> dict[int, list[LeaveBalanceDTO]]:
    """Get active leave balances for employees. Plural by signature."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    target_year = year or date.today().year
    rows = EmployeeLeaveBalance.objects.filter(user_id__in=ids, year=target_year)

    res: dict[int, list[LeaveBalanceDTO]] = {uid: [] for uid in ids}
    for r in rows:
        res[r.user_id].append(
            LeaveBalanceDTO(
                user_id=r.user_id,
                year=r.year,
                leave_category=r.leave_category,
                available_days=r.available_days,
                allocated_days=r.allocated_days,
                availed_days=r.availed_days,
            )
        )
    return res


def get_active_leaves(
    user_ids: Sequence[int],
    on_date: date | None = None,
) -> dict[int, list[ActiveLeaveDTO]]:
    """Get approved active leaves on a given date. Plural by signature."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    target_date = on_date or date.today()
    rows = LeaveApplication.objects.filter(
        user_id__in=ids,
        status="approved",
        start_date__lte=target_date,
        end_date__gte=target_date,
    )

    res: dict[int, list[ActiveLeaveDTO]] = {uid: [] for uid in ids}
    for r in rows:
        res[r.user_id].append(
            ActiveLeaveDTO(
                user_id=r.user_id,
                leave_id=r.pk,
                leave_category=r.leave_category,
                start_date=r.start_date,
                end_date=r.end_date,
                is_station_leave=r.is_station_leave,
                status=r.status,
            )
        )
    return res


def get_leave_records(
    user_ids: Sequence[int],
) -> dict[int, list[ActiveLeaveDTO]]:
    """Get all approved leave history. Plural by signature."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    rows = LeaveApplication.objects.filter(user_id__in=ids, status="approved")
    res: dict[int, list[ActiveLeaveDTO]] = {uid: [] for uid in ids}
    for r in rows:
        res[r.user_id].append(
            ActiveLeaveDTO(
                user_id=r.user_id,
                leave_id=r.pk,
                leave_category=r.leave_category,
                start_date=r.start_date,
                end_date=r.end_date,
                is_station_leave=r.is_station_leave,
                status=r.status,
            )
        )
    return res
