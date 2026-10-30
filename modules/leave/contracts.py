"""Leave public contract. The ONLY file other modules may import.

Plural by signature to prevent N+1 queries across module boundaries.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Sum

from modules.leave.models import LeaveBalance, LeaveRequest
from modules.leave.domain.constants import STATUS_APPROVED


@dataclass(frozen=True)
class LeaveSummaryDTO:
    user_id: int
    active_leaves_count: int
    total_availed_days: Decimal
    balances: dict[str, Decimal]


def get_leave_summaries(user_ids: Sequence[int]) -> dict[int, LeaveSummaryDTO]:
    """Fetch leave summaries for a sequence of user IDs."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    balances_qs = LeaveBalance.objects.filter(user_id__in=ids)
    user_balances: dict[int, dict[str, Decimal]] = {uid: {} for uid in ids}
    for b in balances_qs:
        user_balances[b.user_id][b.category] = b.balance

    requests_qs = (
        LeaveRequest.objects.filter(user_id__in=ids, status=STATUS_APPROVED)
        .values("user_id")
        .annotate(total_days=Sum("requested_days"))
    )
    user_days = {r["user_id"]: r["total_days"] or Decimal("0.0") for r in requests_qs}

    active_counts_qs = (
        LeaveRequest.objects.filter(user_id__in=ids, status=STATUS_APPROVED)
        .values("user_id")
        .annotate(cnt=Sum("id"))
    )
    active_counts = {r["user_id"]: r["cnt"] or 0 for r in active_counts_qs}

    return {
        uid: LeaveSummaryDTO(
            user_id=uid,
            active_leaves_count=active_counts.get(uid, 0),
            total_availed_days=user_days.get(uid, Decimal("0.0")),
            balances=user_balances.get(uid, {}),
        )
        for uid in ids
    }
