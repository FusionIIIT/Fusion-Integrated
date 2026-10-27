"""Public contracts provided by the ELM module to the rest of Fusion."""
from __future__ import annotations

import datetime
from typing import Optional


def is_on_leave(user_id: int, on_date: Optional[datetime.date] = None) -> bool:
    """Check if an employee is currently on approved leave."""
    from modules.elm.models import LeaveRequest, LeaveStatus

    target_date = on_date or datetime.date.today()
    return LeaveRequest.objects.filter(
        applicant_id=user_id,
        status=LeaveStatus.APPROVED,
        start_date__lte=target_date,
        end_date__gte=target_date,
    ).exists()


def get_active_leave(user_id: int, on_date: Optional[datetime.date] = None) -> Optional[dict]:
    """Retrieve details of approved leave for an employee on a given date if any."""
    from modules.elm.models import LeaveRequest, LeaveStatus

    target_date = on_date or datetime.date.today()
    req = LeaveRequest.objects.filter(
        applicant_id=user_id,
        status=LeaveStatus.APPROVED,
        start_date__lte=target_date,
        end_date__gte=target_date,
    ).first()

    if not req:
        return None

    return {
        "request_id": req.id,
        "leave_category": req.category,
        "start_date": req.start_date.isoformat(),
        "end_date": req.end_date.isoformat(),
        "is_station_leave": req.is_station_leave,
    }
