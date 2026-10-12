"""ELM public contract."""
from __future__ import annotations

from collections.abc import Sequence

from modules.elm.models import LeaveBalance, LeaveRequest


def get_leave_requests(user_ids: Sequence[int], *, status: str | None = None
                      ) -> dict[int, list[dict]]:
    """Return leave applications for a group of users.

    The getter is plural on purpose: the list is fetched for a batch and not for
    a single user in isolation.
    """
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    qs = LeaveRequest.objects.filter(user_id__in=ids)
    if status:
        qs = qs.filter(status=status)
    rows = {}
    for user_id in sorted(ids):
        rows[user_id] = [
            {
                "id": req.id,
                "leave_type": req.leave_type,
                "start_date": req.start_date.isoformat(),
                "end_date": req.end_date.isoformat(),
                "days_requested": str(req.days_requested),
                "status": req.status,
            }
            for req in qs.filter(user_id=user_id).order_by("-created_at")
        ]
    return rows


def get_leave_balances(user_ids: Sequence[int]) -> dict[int, dict[str, float]]:
    """Leave balances for a set of users."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    rows = {}
    for user_id in sorted(ids):
        balances = {}
        for balance in LeaveBalance.objects.filter(user_id=user_id):
            balances[balance.leave_type] = {
                "entitled_days": float(balance.entitled_days),
                "used_days": float(balance.used_days),
                "remaining_days": float(balance.remaining_days),
                "year": balance.year,
            }
        rows[user_id] = balances
    return rows
