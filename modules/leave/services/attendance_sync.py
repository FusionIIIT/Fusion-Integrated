"""Transactional handoff to a downstream attendance integration.

No attendance module is installed in this Fusion base. The event is persisted
in the same transaction as the reviewed resumption so a future consumer can
deliver it idempotently without losing the leave-side update.
"""
from datetime import date

from modules.leave.models import AttendanceSyncOutbox, LeaveRequest


def enqueue_resumption_sync(
    request: LeaveRequest, action: str, approved_end_date: date
) -> AttendanceSyncOutbox:
    actual_date = request.actual_resumption_date
    return AttendanceSyncOutbox.objects.create(
        request=request,
        event_key=f"leave-resumption:{request.pk}",
        payload={
            "request_id": request.pk,
            "employee_id": request.applicant_id,
            "category": request.category,
            "leave_start_date": request.start_date.isoformat(),
            "approved_end_date": approved_end_date.isoformat(),
            "recorded_leave_end_date": request.end_date.isoformat(),
            "actual_resumption_date": actual_date.isoformat() if actual_date else None,
            "action": action,
        },
    )
