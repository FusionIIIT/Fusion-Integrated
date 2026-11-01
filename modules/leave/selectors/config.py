"""Reads over the current configuration: policy, hierarchy, calendar, SLA.

"Current" means the row an administrator last saved (BR-EL-030); there is no
draft/publish lifecycle for leave parameters, and the calendar's only version
gate is publication (BR-EL-031).
"""
from __future__ import annotations

from datetime import date

from django.utils import timezone

from modules.leave.domain import categories as cat
from modules.leave.domain.routing import ConfiguredStep
from modules.leave.domain.sla import Thresholds
from modules.leave.models import (
    AcademicVacationPeriod,
    HolidayCalendar,
    LeaveHierarchyStep,
    LeavePolicy,
    SlaThreshold,
)

#: Used when an administrator has not overridden a category yet.
FALLBACK_ENTITLEMENT = dict(cat.ANNUAL_ENTITLEMENT)


def current_policy() -> LeavePolicy:
    row = LeavePolicy.objects.filter(is_active=True).order_by("-id").first()
    if row is None:
        row = LeavePolicy.objects.create(is_active=True,
                                         entitlements=FALLBACK_ENTITLEMENT)
    return row


def entitlement(category: str) -> int:
    policy = current_policy()
    raw = (policy.entitlements or {}).get(category)
    if raw is None:
        raw = FALLBACK_ENTITLEMENT.get(category, 0)
    return int(raw)


def hierarchy_steps() -> tuple[ConfiguredStep, ...]:
    return tuple(
        ConfiguredStep(sequence=row.sequence, kind=row.kind,
                       designation=row.designation,
                       categories=tuple(row.categories or ()))
        for row in LeaveHierarchyStep.objects.filter(is_active=True)
    )


def substitute_categories() -> set[str]:
    return {str(c) for c in (current_policy().substitute_required_categories or [])}


def vacation_periods() -> tuple[tuple[date, date], ...]:
    return tuple((row.start_date, row.end_date)
                 for row in AcademicVacationPeriod.objects.all())


def effective_calendar(on_date: date | None = None) -> HolidayCalendar | None:
    """The published calendar in force on a date (BR-EL-031)."""
    on_date = on_date or timezone.localdate()
    return (HolidayCalendar.objects
            .filter(published_at__isnull=False, effective_from__lte=on_date)
            .order_by("-effective_from", "-version").first())


def closed_dates(start: date, end: date) -> frozenset[date]:
    """Closed holidays inside a period, from the effective calendar."""
    calendar = effective_calendar(start)
    if calendar is None:
        return frozenset()
    return frozenset(calendar.days
                     .filter(kind="holiday", date__gte=start, date__lte=end)
                     .values_list("date", flat=True))


def restricted_holiday_dates(start: date, end: date) -> frozenset[date]:
    calendar = effective_calendar(start)
    if calendar is None:
        return frozenset()
    return frozenset(calendar.days
                     .filter(kind="restricted", date__gte=start, date__lte=end)
                     .values_list("date", flat=True))


def thresholds(task_class: str) -> Thresholds | None:
    row = SlaThreshold.objects.filter(task_class=task_class).first()
    if row is None:
        return None
    return Thresholds(reminder_hours=row.reminder_hours,
                      escalation_hours=row.escalation_hours)
