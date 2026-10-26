"""
modules/leave/contracts.py
Public contract for cross-module consumption of leave data.
"""
from __future__ import annotations

from typing import Sequence


def get_leave_statuses(user_ids: Sequence[int]) -> list[dict]:
    """
    Return pending leave counts for the given user_ids.

    Each entry:
        {
            'user_id': int,
            'pending_count': int,
        }

    Importing is deferred inside the function to avoid circular imports at
    module load time.
    """
    from modules.leave.models import LeaveApplication, ApplicationStatus

    # Build queryset for all pending applications for the requested users
    qs = (
        LeaveApplication.objects
        .filter(
            user_id__in=user_ids,
            status__in=[
                ApplicationStatus.PENDING,
                ApplicationStatus.AWAITING_SUBSTITUTE,
                ApplicationStatus.UNIT_HEAD_REVIEW,
                ApplicationStatus.PROCESSING,
                ApplicationStatus.EXTENSION_PENDING,
                ApplicationStatus.CANCELLATION_PENDING,
            ],
        )
        .values("user_id")
    )

    # Count in Python to keep this simple
    counts: dict[int, int] = {uid: 0 for uid in user_ids}
    for row in qs:
        uid = row["user_id"]
        if uid in counts:
            counts[uid] += 1

    return [{"user_id": uid, "pending_count": cnt} for uid, cnt in counts.items()]
