"""ELM's public surface for other modules. Plural by signature."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ActiveLeaveDTO:
    user_id: int
    has_active_leave: bool
    leave_category: str | None
    start_date: str | None
    end_date: str | None


@dataclass(frozen=True)
class UserBalancesDTO:
    user_id: int
    year: int
    balances: dict[str, float]


def get_active_leaves(user_ids: Sequence[int],
                      on_date: date | None = None) -> dict[int, ActiveLeaveDTO]:
    """Check active approved leaves for multiple users on a given date (plural contract)."""
    from modules.elm.models.leaves import LeaveRequest

    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    target_date = on_date or date.today()
    rows = LeaveRequest.objects.filter(
        user_id__in=ids,
        status="approved",
        start_date__lte=target_date,
        end_date__gte=target_date,
    )

    result = {
        uid: ActiveLeaveDTO(user_id=uid, has_active_leave=False, leave_category=None,
                            start_date=None, end_date=None)
        for uid in ids
    }

    for req in rows:
        result[req.user_id] = ActiveLeaveDTO(
            user_id=req.user_id,
            has_active_leave=True,
            leave_category=req.category,
            start_date=req.start_date.isoformat(),
            end_date=req.end_date.isoformat(),
        )

    return result


def get_leave_balances(user_ids: Sequence[int],
                       year: int) -> dict[int, UserBalancesDTO]:
    """Retrieve leave balances for multiple users for a specific year (plural contract)."""
    from modules.elm.models.balances import LeaveBalance

    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    balances = LeaveBalance.objects.filter(user_id__in=ids, year=year)
    result = {
        uid: UserBalancesDTO(user_id=uid, year=year, balances={})
        for uid in ids
    }

    for b in balances:
        result[b.user_id].balances[b.category] = float(b.available_balance)

    return result
