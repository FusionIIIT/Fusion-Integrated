"""Leave public surface — the ONLY thing other modules may import.

Plural by signature — an N+1 is unwritable.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from modules.leave.models import LeaveBalance


@dataclass(frozen=True)
class LeaveBalanceSummaryDTO:
    user_id: int
    year: int
    balances: list[dict]


def get_leave_balances(user_ids: Sequence[int], year: int) -> dict[int, list[dict]]:
    """Leave balances for multiple users in a given year.

    Returns {user_id: [{"type_code": "CL", "credited": 12, "used": 2, "remaining": 10}, ...]}.
    """
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    rows = (
        LeaveBalance.objects
        .filter(user_id__in=ids, year=year)
        .select_related("leave_type")
        .values("user_id", "leave_type__code", "credited", "used")
    )
    result: dict[int, list[dict]] = {uid: [] for uid in ids}
    for r in rows:
        result[r["user_id"]].append({
            "code": r["leave_type__code"],
            "credited": float(r["credited"]),
            "used": float(r["used"]),
            "remaining": float(r["credited"] - r["used"]),
        })
    return result
