"""Offline-sanctioned leave synchronization service."""

from __future__ import annotations

import datetime

from django.db import transaction
from django.utils import timezone

from modules.leave.domain.counting import count_leave_days
from modules.leave.domain.state_machine import LeaveState
from modules.leave.models import LeaveRequest, LeaveTransition, LedgerEntry
from modules.leave.selectors.calendars import get_active_calendar, get_calendar_holidays


def record_offline_leave(
    user_id: int,
    category: str,
    starts_on: datetime.date,
    ends_on: datetime.date,
    reason: str,
    half: str = "none",
    faculty: bool = True,
    unit: str = "",
    note: str = "",
    recorded_by_user_id: int | None = None,
) -> LeaveRequest:
    """Synchronizes already-sanctioned offline leave under EL-UC-016 and BR-EL-029."""
    calendar = get_active_calendar(starts_on.year)
    holidays = get_calendar_holidays(calendar) if calendar else set()
    days = count_leave_days(category, starts_on, ends_on, half, holidays)

    with transaction.atomic():
        req = LeaveRequest.objects.create(
            user_id=user_id,
            category=category,
            state=LeaveState.APPROVED,
            starts_on=starts_on,
            ends_on=ends_on,
            half=half,
            reason=reason,
            evidence_reference=note,
            requested_days=days,
            actual_days=days,
            decided_at=timezone.now(),
        )

        LeaveTransition.objects.create(
            request=req,
            from_state=LeaveState.DRAFT,
            to_state=LeaveState.APPROVED,
            event="offline_record",
            actor_role="Administrator",
            actor_user_id=recorded_by_user_id,
            remark=f"Offline record: {note}",
            workflow_ref="BR-EL-029",
        )

        LedgerEntry.objects.create(
            user_id=user_id,
            year=starts_on.year,
            category=category,
            days=-abs(days),
            reason="consumption",
            request_id=req.pk,
            note=f"Offline sanctioned leave {req.pk}",
        )

        return req
