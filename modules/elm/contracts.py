"""Cross-module public API for ELM.

All cross-module readers must go through this file, and all getters
must accept sequences of IDs to prevent N+1 queries.
"""
from __future__ import annotations

from collections.abc import Sequence

from modules.elm.models import LeaveApplication


def get_active_leaves_for_employees(
    employee_ids: Sequence[int],
) -> dict[int, list[dict]]:
    """Return active approved/pending leave applications keyed by employee ID."""
    records = LeaveApplication.objects.filter(
        applicant_id__in=employee_ids,
        status__in=["AWAITING_SUBSTITUTE", "AWAITING_APPROVAL", "APPROVED"],
    ).select_related("leave_type")

    result: dict[int, list[dict]] = {emp_id: [] for emp_id in employee_ids}
    for app in records:
        result.setdefault(app.applicant_id, []).append({
            "id": app.id,
            "leave_type": app.leave_type.leave_type,
            "start_date": app.start_date,
            "end_date": app.end_date,
            "status": app.status,
        })
    return result
