"""ELM public surface. The ONLY thing other modules may import.

Plural by signature on purpose (enforces ops/checks/contracts_are_plural.py):
there is no get_active_leave(user_id) because singular lookups cause N+1 query traps.
"""
from __future__ import annotations

import datetime
from collections.abc import Sequence
from dataclasses import dataclass

from modules.elm.models import LeaveApplication, LeaveBalance


@dataclass(frozen=True)
class LeaveRecordDTO:
    application_id: int
    employee_id: int
    leave_type_code: str
    leave_type_name: str
    start_date: datetime.date
    end_date: datetime.date
    days: float
    status: str
    reason: str
    is_station_leave: bool
    station_destination: str


def _to_leave_dto(app: LeaveApplication) -> LeaveRecordDTO:
    return LeaveRecordDTO(
        application_id=app.id,
        employee_id=app.employee_id,
        leave_type_code=app.leave_type.code,
        leave_type_name=app.leave_type.name,
        start_date=app.start_date,
        end_date=app.end_date,
        days=float(app.days),
        status=app.status,
        reason=app.reason,
        is_station_leave=app.is_station_leave,
        station_destination=app.station_destination,
    )


def get_active_leaves(
    user_ids: Sequence[int],
    on_date: datetime.date | None = None,
) -> dict[int, list[LeaveRecordDTO]]:
    """Batched lookup of approved active leaves for given user ids.

    If on_date is supplied, filters for leaves covering that specific calendar date.
    Returns mapping of user_id -> list of LeaveRecordDTO.
    """
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    qs = LeaveApplication.objects.filter(employee_id__in=ids, status="APPROVED").select_related("leave_type")
    if on_date is not None:
        qs = qs.filter(start_date__lte=on_date, end_date__gte=on_date)

    result: dict[int, list[LeaveRecordDTO]] = {uid: [] for uid in ids}
    for app in qs:
        result[app.employee_id].append(_to_leave_dto(app))
    return result


def get_leave_balances(
    user_ids: Sequence[int],
    year: int | None = None,
) -> dict[int, dict[str, float]]:
    """Batched lookup of available leave balances for given user ids.

    Returns mapping of user_id -> {leave_type_code: available_days}.
    """
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    current_year = year or datetime.date.today().year
    qs = LeaveBalance.objects.filter(
        employee_id__in=ids,
        year=current_year,
    ).select_related("leave_type")

    result: dict[int, dict[str, float]] = {uid: {} for uid in ids}
    for bal in qs:
        available = float(bal.allotted - bal.used)
        result[bal.employee_id][bal.leave_type.code] = available
    return result


def get_pending_action_counts(user_ids: Sequence[int]) -> dict[int, int]:
    """Batched lookup of pending actionable items (substitute requests, approvals) for users."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    result: dict[int, int] = {uid: 0 for uid in ids}

    # Count pending substitute requests
    for uid in ids:
        sub_count = LeaveApplication.objects.filter(
            substitute_id=uid,
            status="AWAITING_SUBSTITUTE",
            substitute_status="PENDING",
        ).count()
        result[uid] += sub_count

    return result
