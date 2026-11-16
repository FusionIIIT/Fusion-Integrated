"""Contracts exposed by the Leave Management module.

Cross-module callers may import ONLY this file.
Per platform rule, cross-module getters are plural (they accept a Sequence of user_ids).
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from modules.leave.models import LeaveBalance, LeaveRequest


def get_leave_balances(user_ids: Sequence[int]) -> dict[int, list[dict[str, Any]]]:
    """Retrieve all current leave balances for the given user IDs."""
    ids = list(user_ids)
    if not ids:
        return {}

    records = LeaveBalance.objects.filter(user_id__in=ids)
    result: dict[int, list[dict[str, Any]]] = {uid: [] for uid in ids}
    for b in records:
        result[b.user_id].append({
            "leave_type": b.leave_type,
            "year": b.year,
            "total_entitlement": float(b.total_entitlement),
            "consumed_days": float(b.consumed_days),
            "available_balance": float(b.available_balance),
        })
    return result


def get_active_leave_requests(user_ids: Sequence[int]) -> dict[int, list[dict[str, Any]]]:
    """Retrieve in-flight/pending leave requests for the given user IDs."""
    ids = list(user_ids)
    if not ids:
        return {}

    records = LeaveRequest.objects.filter(
        user_id__in=ids,
        status=LeaveRequest.Status.PENDING_CURRENT_AUTHORITY,
    )
    result: dict[int, list[dict[str, Any]]] = {uid: [] for uid in ids}
    for r in records:
        result[r.user_id].append({
            "id": r.id,
            "leave_type": r.leave_type,
            "start_date": r.start_date.isoformat(),
            "end_date": r.end_date.isoformat(),
            "duration_days": float(r.duration_days),
            "status": r.status,
            "current_authority_id": r.current_authority_id,
        })
    return result


def get_leave_summaries(user_ids: Sequence[int]) -> dict[int, dict[str, Any]]:
    """Retrieve summary counts of approved and pending leaves for the given users."""
    ids = list(user_ids)
    if not ids:
        return {}

    requests = LeaveRequest.objects.filter(user_id__in=ids)
    result: dict[int, dict[str, Any]] = {
        uid: {"approved_count": 0, "pending_count": 0, "total_days_taken": 0.0}
        for uid in ids
    }
    for r in requests:
        if r.status == LeaveRequest.Status.APPROVED:
            result[r.user_id]["approved_count"] += 1
            result[r.user_id]["total_days_taken"] += float(r.duration_days)
        elif r.status == LeaveRequest.Status.PENDING_CURRENT_AUTHORITY:
            result[r.user_id]["pending_count"] += 1
    return result
