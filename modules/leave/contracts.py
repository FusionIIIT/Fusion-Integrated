"""Leave module's public surface. The ONLY thing other modules may import.

Plural by signature on purpose: there is no get_x(id), because a singular
lookup is what gets called inside a loop. Enforced by ops/checks/contracts_are_plural.py.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from modules.leave.models import LeaveApplication, LeaveBalance


@dataclass(frozen=True)
class LeaveBalanceDTO:
    user_id: int
    year: int
    leave_type: str
    credited: Decimal
    availed: Decimal
    balance: Decimal


@dataclass(frozen=True)
class LeaveSummaryDTO:
    application_id: int
    user_id: int
    leave_type: str
    start_date: date
    end_date: date
    days_count: Decimal
    status: str


@dataclass(frozen=True)
class LeaveCountsDTO:
    user_id: int
    pending_count: int
    approved_count: int


def get_leave_balances(
    user_ids: Sequence[int],
    year: int | None = None,
) -> dict[int, list[LeaveBalanceDTO]]:
    """Batched query returning leave balances per user."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    qs = LeaveBalance.objects.filter(user_id__in=ids)
    if year is not None:
        qs = qs.filter(year=year)

    result: dict[int, list[LeaveBalanceDTO]] = {uid: [] for uid in ids}
    for row in qs:
        result[row.user_id].append(
            LeaveBalanceDTO(
                user_id=row.user_id,
                year=row.year,
                leave_type=row.leave_type,
                credited=row.credited,
                availed=row.availed,
                balance=row.balance,
            )
        )
    return result


def get_active_leaves(
    user_ids: Sequence[int],
    on_date: date | None = None,
) -> dict[int, list[LeaveSummaryDTO]]:
    """Batched query returning active/approved leaves covering on_date (defaults to today)."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    target_date = on_date or date.today()
    qs = LeaveApplication.objects.filter(
        applicant_user_id__in=ids,
        status="APPROVED",
        start_date__lte=target_date,
        end_date__gte=target_date,
    )

    result: dict[int, list[LeaveSummaryDTO]] = {uid: [] for uid in ids}
    for row in qs:
        result[row.applicant_user_id].append(
            LeaveSummaryDTO(
                application_id=row.pk,
                user_id=row.applicant_user_id,
                leave_type=row.leave_type,
                start_date=row.start_date,
                end_date=row.end_date,
                days_count=row.days_count,
                status=row.status,
            )
        )
    return result


def get_leave_counts(user_ids: Sequence[int]) -> dict[int, LeaveCountsDTO]:
    """Plural counts of pending and approved leaves per user."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    qs = LeaveApplication.objects.filter(applicant_user_id__in=ids)
    result = {uid: LeaveCountsDTO(user_id=uid, pending_count=0, approved_count=0) for uid in ids}
    for row in qs:
        curr = result[row.applicant_user_id]
        if row.status.startswith("AWAITING_"):
            result[row.applicant_user_id] = LeaveCountsDTO(
                user_id=row.applicant_user_id,
                pending_count=curr.pending_count + 1,
                approved_count=curr.approved_count,
            )
        elif row.status == "APPROVED":
            result[row.applicant_user_id] = LeaveCountsDTO(
                user_id=row.applicant_user_id,
                pending_count=curr.pending_count,
                approved_count=curr.approved_count + 1,
            )
    return result
