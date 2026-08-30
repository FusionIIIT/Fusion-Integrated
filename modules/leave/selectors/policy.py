"""Resolving which policy and which calendar govern a decision.

BR-EL-030, BR-EL-031. A request is judged against what was published and in
force on the day it is decided, not against whatever is current when someone
later opens the record.
"""
from __future__ import annotations

from datetime import date

from django.db.models import Q

from core.api.exceptions import ConflictError
from modules.leave.domain.categories import Category
from modules.leave.domain.counting import Calendar, TailPolicy
from modules.leave.domain.entitlement import CategoryPolicy, ConversionRounding
from modules.leave.models import CategoryRule, Holiday, HolidayCalendar, LeavePolicy


class NoEffectivePolicy(ConflictError):
    """Nothing is published for the date, so no decision can be justified.

    A DomainError rather than a bare exception: this is the state a fresh
    install is in, and the first person to click Apply should be told what is
    missing and who fixes it, not handed a 500.
    """

    code = "no_effective_policy"


def effective_policy(on: date) -> LeavePolicy:
    policy = (
        LeavePolicy.objects.filter(published=True, effective_from__lte=on)
        .filter(Q(effective_to__isnull=True) | Q(effective_to__gt=on))
        .order_by("-effective_from")
        .first()
    )
    if policy is None:
        raise NoEffectivePolicy(
            f"No leave policy is published for {on}. "
            "The leave administrator must publish one before leave can be "
            "applied for."
        )
    return policy


def effective_calendar(year: int) -> HolidayCalendar:
    calendar = (
        HolidayCalendar.objects.filter(year=year, published=True)
        .order_by("-version")
        .first()
    )
    if calendar is None:
        raise NoEffectivePolicy(
            f"No holiday calendar is published for {year}. "
            "The leave administrator must publish one before leave can be "
            "applied for."
        )
    return calendar


def closed_days(calendar: HolidayCalendar) -> Calendar:
    """The calendar as the counting rules want it. Restricted days stay open."""
    days = Holiday.objects.filter(calendar=calendar, restricted=False).values_list(
        "day", flat=True
    )
    return Calendar(holidays=frozenset(days))


def restricted_days(calendar: HolidayCalendar) -> frozenset[date]:
    """BR-EL-003. The dates an RH request may name."""
    return frozenset(
        Holiday.objects.filter(calendar=calendar, restricted=True).values_list(
            "day", flat=True
        )
    )


def category_policies(
    policy: LeavePolicy, *, faculty: bool
) -> dict[Category, CategoryPolicy]:
    """The category settings that apply to this kind of employee."""
    rules = CategoryRule.objects.filter(policy=policy).filter(
        Q(applies_to_faculty__isnull=True) | Q(applies_to_faculty=faculty)
    )
    out: dict[Category, CategoryPolicy] = {}
    for rule in rules:
        category = Category(rule.category)
        # A rule naming this kind of employee beats the one that applies to both.
        if category in out and rule.applies_to_faculty is None:
            continue
        out[category] = CategoryPolicy(
            category=category,
            annual_credit=rule.annual_credit,
            carries_forward=rule.carries_forward,
            carry_forward_cap=rule.carry_forward_cap,
        )
    return out


def requires_evidence(policy: LeavePolicy, category: Category, *, faculty: bool) -> bool:
    """BR-EL-001. Whether this category needs a certificate from this employee."""
    rule = (
        CategoryRule.objects.filter(policy=policy, category=category.value)
        .filter(Q(applies_to_faculty__isnull=True) | Q(applies_to_faculty=faculty))
        .order_by("applies_to_faculty")
        .first()
    )
    return bool(rule and rule.requires_evidence)


def conversion_settings(policy: LeavePolicy) -> tuple[ConversionRounding, TailPolicy]:
    return (
        ConversionRounding(policy.vl_to_el_rounding),
        TailPolicy(policy.early_return_tail),
    )
