"""Maintaining the policy, the calendar, and leave that happened off-system."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError
from modules.leave.domain.categories import (
    Category,
    allows_half_day,
    needs_higher_sanction,
)
from modules.leave.domain.counting import Half, chargeable_days
from modules.leave.domain.state_machine import Actor, Event, State
from modules.leave.models import (
    AuthorityRule,
    CategoryRule,
    EntryReason,
    Holiday,
    HolidayCalendar,
    LeavePolicy,
    LeaveRequest,
    LedgerEntry,
    RequestTransition,
    SlaRule,
    VacationPeriod,
)
from modules.leave.selectors import policy as policy_selector


#: EL-UC-014. Maintaining the policy parameters, BR-EL-030.
def draft_policy(
    *,
    version: str,
    effective_from: date,
    note: str = "",
    vl_to_el_ratio: Decimal | None = None,
    vl_to_el_rounding: str = "",
    early_return_tail: str = "",
    max_backdate_days: int | None = None,
) -> LeavePolicy:
    """Start a new version. It governs nothing until it is published."""
    if LeavePolicy.objects.filter(version=version).exists():
        raise ConflictError(f"Version {version} already exists.", code="version_taken")
    fields = {"version": version, "effective_from": effective_from, "note": note}
    if vl_to_el_ratio is not None:
        fields["vl_to_el_ratio"] = vl_to_el_ratio
    if vl_to_el_rounding:
        fields["vl_to_el_rounding"] = vl_to_el_rounding
    if early_return_tail:
        fields["early_return_tail"] = early_return_tail
    if max_backdate_days is not None:
        fields["max_backdate_days"] = max_backdate_days
    return LeavePolicy.objects.create(published=False, **fields)


def set_category_rule(
    *,
    policy: LeavePolicy,
    category: Category,
    annual_credit: Decimal,
    carries_forward: bool = False,
    carry_forward_cap: Decimal | None = None,
    applies_to_faculty: bool | None = None,
    requires_evidence: bool = False,
) -> CategoryRule:
    """Add or replace one category's entitlement on an unpublished version."""
    _refuse_if_policy_published(policy)
    rule, _ = CategoryRule.objects.update_or_create(
        policy=policy,
        category=category.value,
        applies_to_faculty=applies_to_faculty,
        defaults={
            "annual_credit": annual_credit,
            "carries_forward": carries_forward,
            "carry_forward_cap": carry_forward_cap,
            "requires_evidence": requires_evidence,
        },
    )
    return rule


def set_authority_rule(
    *,
    policy: LeavePolicy,
    category: Category,
    unit: str = "",
    designation: str = "",
    applies_to_faculty: bool | None = None,
    establishment_step: bool = False,
    sanctioning_designation: str = "",
    self_sanction: bool = False,
    specificity: int = 0,
) -> AuthorityRule:
    """BR-EL-019. Who reviews and who sanctions, for one case."""
    _refuse_if_policy_published(policy)
    rule, _ = AuthorityRule.objects.update_or_create(
        policy_id=policy.pk, category=category.value, unit=unit,
        designation=designation,
        defaults={
            "applies_to_faculty": applies_to_faculty,
            "establishment_step": establishment_step,
            "sanctioning_designation": sanctioning_designation,
            "self_sanction": self_sanction,
            "specificity": specificity,
        },
    )
    return rule


def set_sla_rule(
    *,
    policy: LeavePolicy,
    state: str,
    remind_after_hours: int,
    escalate_after_hours: int,
    escalate_to_designation: str = "",
) -> SlaRule:
    """BR-EL-032, BR-EL-033. How long this state may sit before somebody is told."""
    _refuse_if_policy_published(policy)
    if escalate_after_hours <= remind_after_hours:
        raise BadRequestError(
            "Escalation has to come after the reminder, not before it.",
            code="thresholds_out_of_order",
        )
    rule, _ = SlaRule.objects.update_or_create(
        policy_id=policy.pk, state=state,
        defaults={
            "remind_after_hours": remind_after_hours,
            "escalate_after_hours": escalate_after_hours,
            "escalate_to_designation": escalate_to_designation,
        },
    )
    return rule


def _refuse_if_policy_published(policy: LeavePolicy) -> None:
    if policy.published:
        raise ConflictError(
            "A published policy cannot be edited. Draft a new version instead.",
            code="policy_published",
        )


#: EL-UC-015. Maintaining the holiday and RH calendar, BR-EL-031.
def draft_calendar(*, year: int, version: str) -> HolidayCalendar:
    """Start a year's calendar. Holidays go in before it is published."""
    if HolidayCalendar.objects.filter(year=year, version=version).exists():
        raise ConflictError(
            f"Version {version} of the {year} calendar already exists.",
            code="version_taken",
        )
    return HolidayCalendar.objects.create(year=year, version=version, published=False)


def policy_gaps(policy: LeavePolicy) -> list[str]:
    """What would fail if this version governed an application today."""
    entitled = {
        Category(c)
        for c in CategoryRule.objects.filter(policy=policy)
        .values_list("category", flat=True)
        .distinct()
    }
    if not entitled:
        return ["it has no category rules, so it would entitle nobody to anything"]

    routed = set(
        AuthorityRule.objects.filter(policy_id=policy.pk)
        .values_list("category", flat=True)
        .distinct()
    )
    gaps = []
    for category in sorted(entitled, key=lambda c: c.value):
        if category.value not in routed:
            gaps.append(
                f"{category.value} is entitled but has no authority rule, so an "
                "application for it would have nowhere to go")
            continue
        # A higher-sanction category needs a named sanctioner or it strands.
        if not needs_higher_sanction(category):
            continue
        rules = AuthorityRule.objects.filter(
            policy_id=policy.pk, category=category.value)
        resolvable = (
            rules.exclude(sanctioning_designation="").exists()
            or rules.filter(self_sanction=True).exists()
        )
        if not resolvable:
            gaps.append(
                f"{category.value} must be sanctioned above the unit head but no "
                "rule for it names a sanctioning designation")
    return gaps


@transaction.atomic
def publish_policy(*, policy: LeavePolicy, actor_user_id: int) -> LeavePolicy:
    """Put a drafted version in force and close the one it supersedes."""
    if policy.published:
        raise ConflictError("This policy version is already published.", code="published")
    incomplete = policy_gaps(policy)
    if incomplete:
        raise BadRequestError(
            "This version cannot be published yet: " + "; ".join(incomplete),
            code="policy_incomplete",
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
    """EL-UC-016, BR-EL-029: bring leave sanctioned on paper onto the record."""
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
