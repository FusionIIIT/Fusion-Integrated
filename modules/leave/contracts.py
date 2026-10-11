"""Leave module public contract surface."""

from __future__ import annotations

import datetime
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from modules.leave.models import LeaveRequest
from modules.leave.selectors.balances import get_user_balances_summary


@dataclass(frozen=True)
class ActiveLeaveDTO:
    user_id: int
    category: str
    starts_on: datetime.date
    ends_on: datetime.date
    half: str


def get_leave_balances(
    user_ids: Sequence[int], year: int | None = None
) -> dict[int, dict[str, dict[str, Decimal]]]:
    """Returns leave balances for a collection of users."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    target_year = year or datetime.date.today().year
    return {uid: get_user_balances_summary(uid, target_year) for uid in ids}


def get_active_leaves(
    user_ids: Sequence[int], on_date: datetime.date | None = None
) -> dict[int, list[ActiveLeaveDTO]]:
    """Returns active approved leaves covering on_date for a collection of users."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    target_date = on_date or datetime.date.today()
    leaves = LeaveRequest.objects.filter(
        user_id__in=ids,
        state="approved",
        starts_on__lte=target_date,
        ends_on__gte=target_date,
    )
    res: dict[int, list[ActiveLeaveDTO]] = {uid: [] for uid in ids}
    for item in leaves:
        res[item.user_id].append(
            ActiveLeaveDTO(
                user_id=item.user_id,
                category=item.category,
                starts_on=item.starts_on,
                ends_on=item.ends_on,
                half=item.half,
            )
        )
    return res
