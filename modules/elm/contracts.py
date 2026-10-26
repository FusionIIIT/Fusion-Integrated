"""ELM's public contract surface. Plural by signature."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from modules.elm.models import LeaveBalance, LeaveRequest


@dataclass(frozen=True)
class LeaveBalanceDTO:
    user_id: int
    leave_type_id: int
    leave_type_name: str
    year: int
    total_days: int
    used_days: int
    remaining_days: int


@dataclass(frozen=True)
class LeaveSummaryDTO:
    user_id: int
    pending_count: int
    approved_count: int
    rejected_count: int


def get_leave_balances(
    user_ids: Sequence[int], year: int | None = None
) -> dict[int, list[LeaveBalanceDTO]]:
    """Return leave balances for a batch of user_ids."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    qs = LeaveBalance.objects.filter(user_id__in=ids).select_related("leave_type")
    if year is not None:
        qs = qs.filter(year=year)

    result: dict[int, list[LeaveBalanceDTO]] = {uid: [] for uid in ids}
    for b in qs:
        dto = LeaveBalanceDTO(
            user_id=b.user_id,
            leave_type_id=b.leave_type_id,
            leave_type_name=b.leave_type.name,
            year=b.year,
            total_days=b.total_days,
            used_days=b.used_days,
            remaining_days=b.remaining_days,
        )
        result[b.user_id].append(dto)
    return result


def get_leave_summaries(
    user_ids: Sequence[int],
) -> dict[int, LeaveSummaryDTO]:
    """Return counts of leave requests by status for a batch of user_ids."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    qs = LeaveRequest.objects.filter(employee_user_id__in=ids)
    counts: dict[int, dict[str, int]] = {
        uid: {"pending": 0, "approved": 0, "rejected": 0} for uid in ids
    }
    for req in qs:
        status_key = req.status
        if status_key in counts[req.employee_user_id]:
            counts[req.employee_user_id][status_key] += 1

    return {
        uid: LeaveSummaryDTO(
            user_id=uid,
            pending_count=c["pending"],
            approved_count=c["approved"],
            rejected_count=c["rejected"],
        )
        for uid, c in counts.items()
    }
