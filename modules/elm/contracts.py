"""Employee Leave Management public contracts.

The ONLY interface other modules should import for ELM reads.
All getters take sequences to prevent N+1 queries.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from modules.elm.domain.policy import ApplicationStatus
from modules.elm.models import LeaveApplication, LeaveBalance


@dataclass(frozen=True)
class LeaveSummaryDTO:
    application_id: int
    user_id: int
    leave_type_code: str
    leave_type_name: str
    start_date: date
    end_date: date
    status: str
    total_days: Decimal


@dataclass(frozen=True)
class LeaveBalanceDTO:
    user_id: int
    leave_type_code: str
    year: int
    allocated: Decimal
    used: Decimal
    pending: Decimal
    remaining: Decimal


def get_active_leaves_for_users(
    user_ids: Sequence[int], target_date: date | None = None
) -> dict[int, list[LeaveSummaryDTO]]:
    """Return approved leaves for the requested users, optionally covering target_date."""
    user_id_set = set(user_ids)
    if not user_id_set:
        return {}

    qs = LeaveApplication.objects.filter(
        user_id__in=user_id_set,
        status=ApplicationStatus.APPROVED.value,
    ).select_related("leave_type")

    if target_date:
        qs = qs.filter(start_date__lte=target_date, end_date__gte=target_date)

    result: dict[int, list[LeaveSummaryDTO]] = {uid: [] for uid in user_id_set}
    for app in qs:
        result[app.user_id].append(
            LeaveSummaryDTO(
                application_id=app.pk,
                user_id=app.user_id,
                leave_type_code=app.leave_type.code,
                leave_type_name=app.leave_type.name,
                start_date=app.start_date,
                end_date=app.end_date,
                status=app.status,
                total_days=app.total_days,
            )
        )
    return result


def get_leave_balances_for_users(
    user_ids: Sequence[int], year: int
) -> dict[int, list[LeaveBalanceDTO]]:
    """Return leave balances for the requested users for a specific year."""
    user_id_set = set(user_ids)
    if not user_id_set:
        return {}

    qs = LeaveBalance.objects.filter(
        user_id__in=user_id_set,
        year=year,
    ).select_related("leave_type")

    result: dict[int, list[LeaveBalanceDTO]] = {uid: [] for uid in user_id_set}
    for bal in qs:
        result[bal.user_id].append(
            LeaveBalanceDTO(
                user_id=bal.user_id,
                leave_type_code=bal.leave_type.code,
                year=bal.year,
                allocated=bal.allocated,
                used=bal.used,
                pending=bal.pending,
                remaining=bal.remaining,
            )
        )
    return result
