"""Maintaining the policy, the calendar, and leave that happened off-system.

A published policy or calendar is never edited. Correcting one means
superseding it with a new version, because requests already decided cite the
version they were decided under and that citation has to keep meaning what it
said. The same reasoning drives offline recording: rather than editing a
balance, it writes the request and the ledger movement that would have existed
had the leave been applied for here.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError
from modules.leave.domain.categories import Category, allows_half_day
from modules.leave.domain.counting import Half, chargeable_days
from modules.leave.domain.state_machine import Actor, Event, State
from modules.leave.models import (
    CategoryRule,
    EntryReason,
    Holiday,
    HolidayCalendar,
    LeavePolicy,
    LeaveRequest,
    LedgerEntry,
    RequestTransition,
    VacationPeriod,
)
from modules.leave.selectors import policy as policy_selector


@transaction.atomic
def publish_policy(*, policy: LeavePolicy, actor_user_id: int) -> LeavePolicy:
    """Put a drafted version in force and close the one it supersedes."""
    if policy.published:
        raise ConflictError("This policy version is already published.", code="published")
    if not CategoryRule.objects.filter(policy=policy).exists():
        raise BadRequestError(
            "A policy version with no category rules would entitle nobody to anything.",
            code="policy_has_no_rules",
        )

    previous = (
        LeavePolicy.objects.select_for_update()
        .filter(published=True, effective_from__lt=policy.effective_from)
        .filter(effective_to__isnull=True)
        .order_by("-effective_from")
        .first()
    )
    if previous is not None:
        previous.effective_to = policy.effective_from
        previous.save(update_fields=["effective_to", "updated_at"])

    policy.published = True
    policy.save(update_fields=["published", "updated_at"])
    return policy


@transaction.atomic
def publish_calendar(*, calendar: HolidayCalendar, actor_user_id: int) -> HolidayCalendar:
    """Publish a year's calendar. Superseded versions stop being effective."""
    if calendar.published:
        raise ConflictError("This calendar is already published.", code="published")
    if not Holiday.objects.filter(calendar=calendar).exists():
        raise BadRequestError(
            "A calendar with no holidays is almost certainly unfinished.",
            code="calendar_is_empty",
        )
    HolidayCalendar.objects.filter(year=calendar.year, published=True).exclude(
        pk=calendar.pk
    ).update(published=False)
    calendar.published = True
    calendar.save(update_fields=["published", "updated_at"])
    return calendar


def add_holiday(
    *,
    calendar: HolidayCalendar,
    day: date,
    name: str,
    restricted: bool = False,
) -> Holiday:
    _refuse_if_published(calendar)
    return Holiday.objects.create(
        calendar=calendar, day=day, name=name, restricted=restricted
    )


def add_vacation_period(
    *, calendar: HolidayCalendar, name: str, starts_on: date, ends_on: date
) -> VacationPeriod:
    _refuse_if_published(calendar)
    if ends_on < starts_on:
        raise BadRequestError(
            "A vacation period cannot end before it starts.", code="period_invalid"
        )
    return VacationPeriod.objects.create(
        calendar=calendar, name=name, starts_on=starts_on, ends_on=ends_on
    )


def _refuse_if_published(calendar: HolidayCalendar) -> None:
    if calendar.published:
        raise ConflictError(
            "A published calendar cannot be edited. Draft a new version instead.",
            code="calendar_published",
        )


@transaction.atomic
def record_offline(
    *,
    user_id: int,
    category: Category,
    starts_on: date,
    ends_on: date,
    reason: str,
    recorded_by_user_id: int,
    faculty: bool = False,
    half: Half | None = None,
    unit: str = "",
    note: str = "",
) -> LeaveRequest:
    """Bring leave sanctioned on paper onto the record. EL-UC-016, BR-EL-029.

    This is the one path that does not go through the workflow, because the
    specification retires it as a workflow on purpose: the leave was already
    sanctioned elsewhere and re-approving it here would be a second approval.
    The request is therefore born closed, carrying its ledger movement and the
    name of whoever entered it, so a balance can always be traced to either a
    decision this system took or a decision it was told about.
    """
    if ends_on < starts_on:
        raise BadRequestError("Leave cannot end before it starts.", code="period_invalid")
    if half is not None and not allows_half_day(category):
        raise BadRequestError(
            f"{category.value} cannot be taken as a half day.", code="half_day_not_allowed"
        )
    if recorded_by_user_id == user_id:
        raise BadRequestError(
            "Offline leave is entered by the leave administrator, not by the employee.",
            code="self_recorded",
        )

    effective = policy_selector.effective_policy(starts_on)
    calendar = policy_selector.effective_calendar(starts_on.year)
    days = chargeable_days(
        category, starts_on, ends_on, policy_selector.closed_days(calendar), half=half
    )
    if days <= Decimal("0"):
        raise BadRequestError(
            "The period contains no chargeable days.", code="no_chargeable_days"
        )
    if LedgerEntry.objects.filter(
        user_id=user_id,
        year=starts_on.year,
        category=category.value,
        reason=EntryReason.OFFLINE_RECORDED,
        note=_marker(starts_on, ends_on),
    ).exists():
        raise ConflictError(
            "This period is already on the record for this employee.",
            code="already_recorded",
        )

    request = LeaveRequest.objects.create(
        user_id=user_id,
        category=category.value,
        state=State.CLOSED.value,
        starts_on=starts_on,
        ends_on=ends_on,
        half=half.value if half else "",
        reason=reason,
        requested_days=days,
        actual_days=days,
        policy_id=effective.pk,
        calendar_id=calendar.pk,
        unit=unit,
        decided_at=timezone.now(),
    )
    RequestTransition.objects.create(
        request=request,
        from_state=State.DRAFT.value,
        to_state=State.CLOSED.value,
        event=Event.OFFLINE_RECORD.value,
        actor_role=Actor.LEAVE_ADMINISTRATOR.value,
        actor_user_id=recorded_by_user_id,
        remark=note,
    )
    LedgerEntry.objects.create(
        user_id=user_id,
        year=starts_on.year,
        category=category.value,
        days=-days,
        reason=EntryReason.OFFLINE_RECORDED,
        request_id=request.pk,
        policy_id=effective.pk,
        recorded_by_user_id=recorded_by_user_id,
        note=_marker(starts_on, ends_on),
    )
    return request


def _marker(starts_on: date, ends_on: date) -> str:
    return f"Offline sanction {starts_on} to {ends_on}"
