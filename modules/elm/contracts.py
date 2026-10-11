"""elm's public surface. Plural by signature.

A caller with many ids gets one mapping back, so the batched form is the only
form — the N+1 is unwritable, not merely discouraged.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.utils import timezone

from modules.elm.models import LeaveApplication
from modules.elm.selectors import queries


@dataclass(frozen=True)
class LeaveBalanceDTO:
    user_id: int
    year: int
    leave_type: str
    entitled_days: Decimal
    used_days: Decimal
    available_days: Decimal


def get_leave_balances(user_ids: Sequence[int], year: int
                       ) -> dict[int, tuple[LeaveBalanceDTO, ...]]:
    """Every balance bucket for the given people, for one year."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    rows = queries.balances_for_users(ids, year)
    return {
        uid: tuple(
            LeaveBalanceDTO(uid, year, b.leave_type.code, b.entitled, b.used,
                            b.available)
            for b in rows.get(uid, [])
        )
        for uid in sorted(ids)
    }


@dataclass(frozen=True)
class LeaveAvailabilityDTO:
    user_id: int
    on_leave: bool
    application_id: int | None


def get_leave_availability(user_ids: Sequence[int], on_date: date | None = None
                           ) -> dict[int, LeaveAvailabilityDTO]:
    """Whether someone is on approved leave on a date — for HR and payroll."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    day = on_date or timezone.localdate()
    live = dict(
        LeaveApplication.objects
        .filter(user_id__in=ids, status="approved",
                start_date__lte=day, end_date__gte=day)
        .values_list("user_id", "pk"))
    return {uid: LeaveAvailabilityDTO(uid, uid in live, live.get(uid))
            for uid in sorted(ids)}
