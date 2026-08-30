"""leave's public surface. Plural by signature."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from modules.leave.domain.state_machine import State
from modules.leave.models import LeaveRequest
from modules.leave.selectors import balances

ACTIVE = (State.ONGOING.value, State.AWAITING_RESUMPTION.value)


@dataclass(frozen=True)
class OnLeaveDTO:
    user_id: int
    category: str
    starts_on: date
    ends_on: date


@dataclass(frozen=True)
class LeaveBalanceDTO:
    user_id: int
    category: str
    available: Decimal


def get_absences(user_ids: Sequence[int], on: date) -> dict[int, OnLeaveDTO]:
    """Who among these people is away on this date.

    Another module asking "can this person be scheduled" wants one call for the
    whole list, so the answer is keyed by user.
    """
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    rows = LeaveRequest.objects.filter(
        user_id__in=ids,
        state__in=(*ACTIVE, State.APPROVED_NOT_STARTED.value),
        starts_on__lte=on,
        ends_on__gte=on,
    ).only("user_id", "category", "starts_on", "ends_on")
    return {
        r.user_id: OnLeaveDTO(
            user_id=r.user_id,
            category=r.category,
            starts_on=r.starts_on,
            ends_on=r.ends_on,
        )
        for r in rows
    }


def get_balances(
    user_ids: Sequence[int], year: int, category: str
) -> dict[int, LeaveBalanceDTO]:
    """What each of these people has left in one category."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    from modules.leave.domain.categories import Category

    wanted = Category(category)
    out: dict[int, LeaveBalanceDTO] = {}
    for user_id in ids:
        balance = balances.balance_for(user_id, year, wanted)
        out[user_id] = LeaveBalanceDTO(
            user_id=user_id, category=category, available=balance.available
        )
    return out
