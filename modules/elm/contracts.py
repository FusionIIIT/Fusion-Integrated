"""ELM's public surface for other modules. Plural by signature."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from modules.elm.models.balances import LeaveBalance
from modules.elm.models.leaves import LeaveRequest


@dataclass(frozen=True)
class ActiveLeaveDTO:
    user_id: int
    has_active_leave: bool
    category: str | None = None
    start_date: str | None = None
    end_date: str | None = None


@dataclass(frozen=True)
class UserBalancesDTO:
    user_id: int
    year: int
    balances: dict[str, float]


def get_active_leaves(
    user_ids: Sequence[int],
    on_date: date | None = None,
) -> dict[int, ActiveLeaveDTO]:
    """Check active approved leaves for multiple users on a given date (plural contract)."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    target = on_date or date.today()
    active_records = LeaveRequest.objects.filter(
        user_id__in=ids,
        status="approved",
        start_date__lte=target,
        end_date__gte=target,
    )

    by_user = {r.user_id: r for r in active_records}
    result = {}
    for uid in ids:
        rec = by_user.get(uid)
        if rec:
            result[uid] = ActiveLeaveDTO(
                user_id=uid,
                has_active_leave=True,
                category=rec.category,
                start_date=str(rec.start_date),
                end_date=str(rec.end_date),
            )
        else:
            result[uid] = ActiveLeaveDTO(
                user_id=uid,
                has_active_leave=False,
            )
    return result


def get_user_balances(
    user_ids: Sequence[int],
    year: int | None = None,
) -> dict[int, UserBalancesDTO]:
    """Retrieve category available balances for multiple users in a calendar year (plural contract)."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    target_year = year or date.today().year
    records = LeaveBalance.objects.filter(user_id__in=ids, year=target_year)

    user_map: dict[int, dict[str, float]] = {uid: {} for uid in ids}
    for r in records:
        user_map[r.user_id][r.category] = float(r.available_balance)

    return {
        uid: UserBalancesDTO(user_id=uid, year=target_year, balances=user_map[uid])
        for uid in ids
    }
