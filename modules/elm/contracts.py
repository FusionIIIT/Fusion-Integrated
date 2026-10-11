"""Public contract for the ELM module.

The ONLY thing other modules may import from modules.elm.
All getters are plural by signature (takes a sequence of ids) to prevent N+1 queries.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.utils import timezone

from modules.elm.domain.constants import ApplicationStatus
from modules.elm.models import LeaveAccount, LeaveApplication


@dataclass(frozen=True)
class LeaveBalanceDTO:
    user_id: int
    year: int
    category: str
    balance: Decimal


@dataclass(frozen=True)
class ActiveLeaveDTO:
    application_id: int
    user_id: int
    category: str
    start_date: date
    end_date: date
    chargeable_days: Decimal
    status: str
    is_station_leave: bool
    station_destination: str


def get_leave_balances(
    user_ids: Sequence[int],
    year: int | None = None,
) -> dict[int, dict[str, Decimal]]:
    """Return leave balances keyed by user_id -> category -> balance."""
    uids = {int(u) for u in user_ids if u is not None}
    if not uids:
        return {}

    target_year = year or timezone.now().year
    accounts = LeaveAccount.objects.filter(user_id__in=uids, year=target_year)

    res: dict[int, dict[str, Decimal]] = {u: {} for u in uids}
    for acc in accounts:
        res[acc.user_id][acc.category] = acc.balance
    return res


def get_active_leaves(
    user_ids: Sequence[int],
    on_date: date | None = None,
) -> dict[int, list[ActiveLeaveDTO]]:
    """Return approved leaves active on a given date for the specified users."""
    uids = {int(u) for u in user_ids if u is not None}
    if not uids:
        return {}

    target_date = on_date or timezone.now().date()
    apps = LeaveApplication.objects.filter(
        user_id__in=uids,
        status=ApplicationStatus.APPROVED.value,
        start_date__lte=target_date,
        end_date__gte=target_date,
    )

    res: dict[int, list[ActiveLeaveDTO]] = {u: [] for u in uids}
    for a in apps:
        res[a.user_id].append(
            ActiveLeaveDTO(
                application_id=a.id,
                user_id=a.user_id,
                category=a.category,
                start_date=a.start_date,
                end_date=a.end_date,
                chargeable_days=a.chargeable_days,
                status=a.status,
                is_station_leave=a.is_station_leave,
                station_destination=a.station_destination,
            )
        )
    return res


def get_leave_applications(
    application_ids: Sequence[int],
) -> dict[int, ActiveLeaveDTO]:
    """Return leave applications by ID."""
    app_ids = {int(i) for i in application_ids if i is not None}
    if not app_ids:
        return {}

    apps = LeaveApplication.objects.filter(id__in=app_ids)
    return {
        a.id: ActiveLeaveDTO(
            application_id=a.id,
            user_id=a.user_id,
            category=a.category,
            start_date=a.start_date,
            end_date=a.end_date,
            chargeable_days=a.chargeable_days,
            status=a.status,
            is_station_leave=a.is_station_leave,
            station_destination=a.station_destination,
        )
        for a in apps
    }
