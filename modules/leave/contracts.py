"""Contracts for Leave Management — read-only, plural, for other modules."""
from datetime import date
from typing import Optional, Sequence

from .models import LeaveBalance, LeaveRequest
from .selectors.leave_requests import (
    get_leave_balance,
    get_user_balances,
    get_overlapping_requests,
)
from .selectors.balances import get_user_balances as get_balances_selector


def get_user_leave_balances(user_ids: Sequence[int], year: int) -> dict[int, list]:
    """Get all leave balances for multiple users in a year."""
    balances = LeaveBalance.objects.filter(user_id__in=user_ids, year=year)
    result: dict[int, list] = {uid: [] for uid in user_ids}
    for bal in balances:
        result[bal.user_id].append({
            "category": bal.category,
            "opening_balance": str(bal.opening_balance),
            "credited": str(bal.credited),
            "availed": str(bal.availed),
            "lapsed": str(bal.lapsed),
            "closing_balance": str(bal.closing_balance),
        })
    return result


def get_user_pending_leave_counts(user_ids: Sequence[int]) -> dict[int, int]:
    """Get count of pending leave requests per user."""
    from django.db.models import Count

    rows = LeaveRequest.objects.filter(
        user_id__in=user_ids,
        status__in=[
            "submitted",
            "substitute_pending",
            "unit_head_review",
            "establishment_review",
            "final_sanction",
            "approved",
        ],
    ).values("user_id").annotate(count=Count("pk"))

    result = {uid: 0 for uid in user_ids}
    for row in rows:
        result[row["user_id"]] = row["count"]
    return result


def get_user_leave_summary(user_ids: Sequence[int], year: int) -> dict[int, dict]:
    """Get leave summary for multiple users."""
    balances = get_user_leave_balances(user_ids, year)
    pending_counts = get_user_pending_leave_counts(user_ids)

    result = {}
    for uid in user_ids:
        result[uid] = {
            "balances": balances.get(uid, []),
            "pending_count": pending_counts.get(uid, 0),
        }
    return result


def is_user_on_leave(user_ids: Sequence[int], on_date: date) -> dict[int, bool]:
    """Check if users are on approved leave on a specific date."""
    from django.db.models import Q

    rows = LeaveRequest.objects.filter(
        user_id__in=user_ids,
        status="approved",
        start_date__lte=on_date,
        end_date__gte=on_date,
    ).values_list("user_id", flat=True).distinct()

    on_leave = set(rows)
    return {uid: uid in on_leave for uid in user_ids}