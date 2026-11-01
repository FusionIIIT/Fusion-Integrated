"""Leave module's public contract surface. Plural by signature."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field


@dataclass(frozen=True)
class LeaveApplicationContract:
    user_id: int
    category: str
    start_date: str
    end_date: str
    reason: str
    half_day_cl: bool
    station_leave_details: dict = field(default_factory=dict)
    substitute_id: int | None = None
    status: str = "draft"
    posting_id: int = 0


@dataclass(frozen=True)
class LeaveBalanceContract:
    user_id: int
    year: int
    balance: float


@dataclass(frozen=True)
class LeaveApplicationAuditContract:
    application_id: int
    status: str
    reason: str
    at: str


def get_leave_balances(
    user_ids: Sequence[int],
    year: int,
) -> dict[int, LeaveBalanceContract]:
    """Query leave balances for multiple users in a given year. Plural by signature."""
    from modules.leave.models import LeaveBalance

    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    rows = LeaveBalance.objects.filter(user_id__in=ids, year=year)
    return {
        row.user_id: LeaveBalanceContract(
            user_id=row.user_id,
            year=row.year,
            balance=float(row.balance),
        )
        for row in rows
    }


def get_active_leave_applications(
    user_ids: Sequence[int],
) -> dict[int, list[LeaveApplicationContract]]:
    """Query active leave applications for multiple users. Plural by signature."""
    from modules.leave.models import LeaveApplication

    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    apps = (
        LeaveApplication.objects.filter(user_id__in=ids)
        .exclude(status__in=["rejected", "withdrawn", "cancelled", "closed"])
        .order_by("-created_at")
    )
    result: dict[int, list[LeaveApplicationContract]] = {uid: [] for uid in ids}
    for app in apps:
        result[app.user_id].append(
            LeaveApplicationContract(
                user_id=app.user_id,
                category=app.category,
                start_date=str(app.start_date),
                end_date=str(app.end_date),
                reason=app.reason,
                half_day_cl=app.half_day_cl,
                station_leave_details=app.station_leave_details,
                substitute_id=app.substitute_id,
                status=app.status,
                posting_id=getattr(app, "posting_id", 0),
            )
        )
    return result
