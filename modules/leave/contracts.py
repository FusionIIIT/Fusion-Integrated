"""leave's public surface. Plural by signature, so an N+1 is unwritable.

Another module that needs to know who is away (scheduling an interview, chasing
a clearance, planning a training session) asks here rather than reading these
tables. Nothing in this file mutates: a module that needs a change here needs an
event, not a setter.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from modules.leave.domain import state_machine as sm
from modules.leave.models import LeaveBalance, LeaveRequest


@dataclass(frozen=True)
class LeaveStatusDTO:
    """Whether one person is away on a date, and until when."""

    user_id: int
    on_leave: bool
    category: str = ""
    until: date | None = None


def get_leave_statuses(user_ids: Sequence[int],
                       on_date: date) -> dict[int, LeaveStatusDTO]:
    """Who is on approved leave on `on_date`, for a whole batch of people."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    rows = (LeaveRequest.objects
            .filter(user_id__in=ids, status__in=(sm.APPROVED, sm.EXTENDED),
                    period_from__lte=on_date, period_to__gte=on_date)
            .values_list("user_id", "category", "period_to"))
    found: dict[int, LeaveStatusDTO] = {}
    for user_id, category, period_to in rows:
        found[user_id] = LeaveStatusDTO(user_id, True, category, period_to)
    return {uid: found.get(uid, LeaveStatusDTO(uid, False)) for uid in ids}


@dataclass(frozen=True)
class LeaveAvailabilityDTO:
    """One person's remaining balance, as another module may need it."""

    user_id: int
    leave_year: int
    available_by_category: dict[str, str]
    on_leave_today: bool


def get_leave_availabilities(user_ids: Sequence[int], leave_year: int
                             ) -> dict[int, LeaveAvailabilityDTO]:
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    rows = LeaveBalance.objects.filter(user_id__in=ids, leave_year=leave_year)
    balances: dict[int, dict[str, str]] = {uid: {} for uid in ids}
    for row in rows:
        balances[row.user_id][row.category] = str(row.available_days)
    today = date.today()
    today_status = get_leave_statuses(sorted(ids), today)
    return {
        uid: LeaveAvailabilityDTO(uid, leave_year, balances[uid],
                                  today_status[uid].on_leave)
        for uid in sorted(ids)
    }
