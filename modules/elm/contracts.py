"""Cross-module contracts for ELM (ADR-0013).

Other modules can only import from here, never from elm models or services directly.
"""
from dataclasses import dataclass
from datetime import date
from typing import Sequence

from .models import LeaveApplication


@dataclass(frozen=True)
class UserOnLeaveDTO:
    user_id: int
    category: str
    leave_start: date
    leave_end: date
    station_leave_required: bool


def get_active_leaves(user_ids: Sequence[int], target_date: date) -> dict[int, UserOnLeaveDTO]:
    """Return users currently on approved leave on target_date."""
    apps = LeaveApplication.objects.filter(
        user_id__in=user_ids,
        status="approved",
        leave_start__lte=target_date,
        leave_end__gte=target_date,
    )
    return {
        a.user_id: UserOnLeaveDTO(
            user_id=a.user_id,
            category=a.category,
            leave_start=a.leave_start,
            leave_end=a.leave_end,
            station_leave_required=a.station_leave_required,
        )
        for a in apps
    }
