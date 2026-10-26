"""The ONLY door other modules may reach into the leave module through.

Enforced by .importlinter and ops/checks/contracts_are_plural.py.
"""
from typing import Sequence

MODULE_CODE = "leave_module"

PERMISSION_LEAVE_CREATE = "leave_module.request.create"
PERMISSION_LEAVE_VIEW_SELF = "leave_module.request.view_self"
PERMISSION_SUBSTITUTE_RESPOND = "leave_module.substitute.respond"
PERMISSION_LEAVE_REVIEW = "leave_module.request.review"
PERMISSION_LEAVE_ADMIN = "leave_module.admin.manage"


def get_leave_requests(request_ids: Sequence[int]) -> list[dict]:
    """Retrieve multiple leave requests by their IDs (plural contract)."""
    from modules.leave.models import LeaveRequest

    requests = LeaveRequest.objects.filter(id__in=request_ids)
    return [
        {
            "id": r.id,
            "user_id": r.user_id,
            "category": r.category,
            "start_date": r.start_date,
            "end_date": r.end_date,
            "computed_days": r.computed_days,
            "status": r.status,
            "reason": r.reason,
        }
        for r in requests
    ]


def get_user_leave_balances(user_ids: Sequence[int], year: int) -> dict[int, list[dict]]:
    """Retrieve leave balances for multiple users in a given year (plural contract)."""
    from modules.leave.models import LeaveBalance

    balances = LeaveBalance.objects.filter(user_id__in=user_ids, year=year)
    result: dict[int, list[dict]] = {uid: [] for uid in user_ids}
    for b in balances:
        result.setdefault(b.user_id, []).append({
            "category": b.category,
            "credited": b.credited,
            "availed": b.availed,
            "balance": b.balance,
        })
    return result
