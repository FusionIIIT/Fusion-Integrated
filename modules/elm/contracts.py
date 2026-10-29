"""Public cross-module interface for Employee Leave Management.

All getters take a sequence of user IDs to prevent N+1 queries across boundaries.
"""
from __future__ import annotations

import datetime
from collections.abc import Sequence
from dataclasses import dataclass

from django.utils import timezone

from modules.elm.domain.state_machine import LeaveStatus
from modules.elm.models import LeaveApplication


@dataclass(frozen=True)
class EmployeeLeaveStatusDTO:
    user_id: int
    is_on_leave: bool
    active_leave_category: str | None = None
    pending_count: int = 0
    approved_count: int = 0


def get_employee_leave_statuses(
    user_ids: Sequence[int],
    as_of_date: datetime.date | None = None,
) -> dict[int, EmployeeLeaveStatusDTO]:
    """Return current leave status and counts for the requested user IDs."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    target_date = as_of_date or timezone.now().date()

    apps = LeaveApplication.objects.filter(
        user_id__in=ids,
        status__in=[LeaveStatus.PENDING.value, LeaveStatus.APPROVED.value],
    )

    pending_counts: dict[int, int] = {}
    approved_counts: dict[int, int] = {}
    active_leaves: dict[int, str] = {}

    for app in apps:
        if app.status == LeaveStatus.PENDING.value:
            pending_counts[app.user_id] = pending_counts.get(app.user_id, 0) + 1
        elif app.status == LeaveStatus.APPROVED.value:
            approved_counts[app.user_id] = approved_counts.get(app.user_id, 0) + 1
            if app.start_date <= target_date <= app.end_date:
                active_leaves[app.user_id] = app.category

    return {
        uid: EmployeeLeaveStatusDTO(
            user_id=uid,
            is_on_leave=uid in active_leaves,
            active_leave_category=active_leaves.get(uid),
            pending_count=pending_counts.get(uid, 0),
            approved_count=approved_counts.get(uid, 0),
        )
        for uid in ids
    }
