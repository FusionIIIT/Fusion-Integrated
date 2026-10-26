"""Contracts exposed by ELM for other modules.

Every getter must be plural per Fusion integration conventions.
"""
from collections.abc import Sequence

from .models import LeaveApplication, LeaveBalance


def get_active_leave_counts(user_ids: Sequence[int]) -> dict[int, int]:
    """Return count of active leaves for each user in user_ids."""
    counts = dict.fromkeys(user_ids, 0)
    qs = LeaveApplication.objects.filter(
        applicant_id__in=user_ids,
        status__in=[
            "submitted",
            "pending_substitute",
            "pending_unit_head",
            "pending_sanction",
            "approved",
        ],
    )
    for app in qs:
        counts[app.applicant_id] = counts.get(app.applicant_id, 0) + 1
    return counts


def get_user_leave_balances(user_ids: Sequence[int]) -> dict[int, list[dict]]:
    """Return leave balances for each user in user_ids."""
    balances = {uid: [] for uid in user_ids}
    qs = LeaveBalance.objects.filter(user_id__in=user_ids)
    for b in qs:
        balances[b.user_id].append({
            "leave_type": b.leave_type,
            "allocated": float(b.allocated),
            "used": float(b.used),
            "balance": float(b.balance),
            "year": b.year,
        })
    return balances
