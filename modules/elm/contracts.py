"""ELM public contract surface.

Plural by signature per ADR-0013 and ops/checks/contracts_are_plural.py.
Only functions taking sequences of IDs are exposed for cross-module consumption.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Dict, List


@dataclass(frozen=True)
class ActiveLeaveDTO:
    user_id: int
    has_active_leave: bool
    leave_type_code: str = ""
    start_date: str = ""
    end_date: str = ""


@dataclass(frozen=True)
class EmployeeLeaveSummaryDTO:
    user_id: int
    pending_requests_count: int
    approved_leaves_count: int


def get_active_leaves_on_date(
    user_ids: Sequence[int], target_date: date
) -> Dict[int, ActiveLeaveDTO]:
    """Check whether employees have approved active leave on a given date.

    Plural by signature to prevent N+1 queries.
    """
    from modules.elm.models import LeaveRequest
    from modules.elm.domain.state_machine import Status

    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    leaves = LeaveRequest.objects.filter(
        employee_user_id__in=ids,
        status=Status.APPROVED.value,
        start_date__lte=target_date,
        end_date__gte=target_date,
    ).select_related("leave_type")

    result: Dict[int, ActiveLeaveDTO] = {
        uid: ActiveLeaveDTO(user_id=uid, has_active_leave=False) for uid in ids
    }
    for leave in leaves:
        result[leave.employee_user_id] = ActiveLeaveDTO(
            user_id=leave.employee_user_id,
            has_active_leave=True,
            leave_type_code=leave.leave_type.code,
            start_date=str(leave.start_date),
            end_date=str(leave.end_date),
        )
    return result


def get_employee_leave_summaries(
    user_ids: Sequence[int],
) -> Dict[int, EmployeeLeaveSummaryDTO]:
    """Return aggregated count of pending and approved leaves for employees."""
    from modules.elm.models import LeaveRequest
    from modules.elm.domain.state_machine import Status

    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    result = {
        uid: EmployeeLeaveSummaryDTO(
            user_id=uid,
            pending_requests_count=0,
            approved_leaves_count=0,
        )
        for uid in ids
    }

    requests = LeaveRequest.objects.filter(employee_user_id__in=ids)
    for req in requests:
        summary = result[req.employee_user_id]
        is_approved = req.status == Status.APPROVED.value
        is_pending = req.status in {
            Status.PENDING_UNIT_HEAD.value,
            Status.PENDING_ESTABLISHMENT.value,
            Status.PENDING_FINAL_SANCTION.value,
            Status.AWAITING_SUBSTITUTE_RESPONSE.value,
            Status.AWAITING_DIRECTOR_SELF_SANCTION.value,
        }
        result[req.employee_user_id] = EmployeeLeaveSummaryDTO(
            user_id=req.employee_user_id,
            pending_requests_count=summary.pending_requests_count + (1 if is_pending else 0),
            approved_leaves_count=summary.approved_leaves_count + (1 if is_approved else 0),
        )

    return result
