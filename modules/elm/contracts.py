"""ELM contracts for cross-module consumption.

All getters take a Sequence of user IDs to guarantee batching and prevent N+1 queries.
Validated by ops/checks/contracts_are_plural.py.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Any

from django.utils import timezone

from modules.elm.models import LeaveApplication, LeaveBalance


def get_leave_balances(
    user_ids: Sequence[int], year: int = 2026
) -> dict[int, list[dict[str, Any]]]:
    """Return leave balances for the requested user IDs."""
    balances = LeaveBalance.objects.filter(
        user_id__in=user_ids,
        year=year,
    ).select_related("category")

    result: dict[int, list[dict[str, Any]]] = {uid: [] for uid in user_ids}
    for b in balances:
        result[b.user_id].append({
            "category_code": b.category.code,
            "category_name": b.category.name,
            "balance": float(b.balance),
            "credited": float(b.credited),
            "consumed": float(b.consumed),
        })
    return result


def get_active_leaves(
    user_ids: Sequence[int],
) -> dict[int, list[dict[str, Any]]]:
    """Return currently active or approved leaves for the requested user IDs."""
    leaves = LeaveApplication.objects.filter(
        user_id__in=user_ids,
        status=LeaveApplication.STATUS_APPROVED,
    ).select_related("category")

    result: dict[int, list[dict[str, Any]]] = {uid: [] for uid in user_ids}
    for item in leaves:
        result[item.user_id].append({
            "id": item.id,
            "category_code": item.category.code,
            "start_date": item.start_date.isoformat(),
            "end_date": item.end_date.isoformat(),
            "days_count": float(item.days_count),
        })
    return result


def get_employee_on_leave_status(
    user_ids: Sequence[int],
    on_date: date | None = None,
) -> dict[int, bool]:
    """Return whether each requested employee is currently on approved leave on the given date."""
    target_date = on_date or timezone.now().date()
    on_leave_users = set(
        LeaveApplication.objects.filter(
            user_id__in=user_ids,
            status=LeaveApplication.STATUS_APPROVED,
            start_date__lte=target_date,
            end_date__gte=target_date,
        ).values_list("user_id", flat=True)
    )
    return {uid: (uid in on_leave_users) for uid in user_ids}
