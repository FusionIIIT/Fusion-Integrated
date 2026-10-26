"""elm's public surface. Plural by signature."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from modules.elm.models import LeaveApplication, LeaveBalance


@dataclass(frozen=True)
class LeaveBalanceDTO:
    user_id: int
    year: int
    category: str
    available: Decimal


def get_leave_balances(user_ids: Sequence[int],
                       year: int) -> dict[int, list[LeaveBalanceDTO]]:
    """Available leave per category, for several employees at once.

    Plural because a roster screen or a scheduler checks a group, not a person;
    there is intentionally no singular version.
    """
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    rows = LeaveBalance.objects.filter(user_id__in=ids, year=year)
    out: dict[int, list[LeaveBalanceDTO]] = {uid: [] for uid in ids}
    for b in rows:
        out[b.user_id].append(LeaveBalanceDTO(b.user_id, b.year, b.category,
                                              b.available))
    return out


def active_leave_user_ids(user_ids: Sequence[int], start, end) -> set[int]:
    """Which of these employees have approved leave over the interval."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return set()
    qs = (LeaveApplication.objects
          .filter(user_id__in=ids, status="approved",
                  start_date__lte=end, end_date__gte=start))
    return set(qs.values_list("user_id", flat=True))
