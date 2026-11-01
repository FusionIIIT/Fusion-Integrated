"""Maintaining the current configuration (EL-UC-014, EL-UC-015, EL-UC-018).

No lifecycle here beyond the calendar's publication flag: BR-EL-030 says
validation and routing use the current configured values, so a saved change is
live, and the calendar is the one thing that waits to be published (BR-EL-031).
"""
from __future__ import annotations

import logging
from datetime import date

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError
from modules.leave.domain import categories as cat
from modules.leave.domain import routing
from modules.leave.domain import sla as sla_domain
from modules.leave.domain.errors import RuleViolation
from modules.leave.models import (
    AcademicVacationPeriod,
    HolidayCalendar,
    HolidayCalendarDay,
    LeaveHierarchyStep,
    LeavePolicy,
    SlaThreshold,
)
from modules.leave.services import authz

log = logging.getLogger("fusion.leave.config")


@transaction.atomic
def update_policy(*, actor, entitlements: dict | None = None,
                  substitute_categories: list[str] | None = None,
                  max_backdate_days: int | None = None,
                  self_sanction_designation: str | None = None,
                  notes: str = "") -> LeavePolicy:
    """EL-UC-014: save the current policy parameters."""
    authz.require(actor, "leave.policy.update")
    row, _ = LeavePolicy.objects.get_or_create(is_active=True)

    if entitlements is not None:
        unknown = sorted(set(entitlements) - set(cat.CATEGORIES))
        if unknown:
            raise ConflictError(f"{', '.join(unknown)} is not a leave category.",
                                code="unknown_category")
        row.entitlements = {**row.entitlements, **entitlements}
    if substitute_categories is not None:
        row.substitute_required_categories = sorted(substitute_categories)
    if max_backdate_days is not None:
        row.max_backdate_days = max_backdate_days
    if self_sanction_designation is not None:
        row.self_sanction_designation = self_sanction_designation
    if notes:
        row.notes = notes
    row.updated_by_user_id = getattr(actor, "user_id", None)
    row.save()
    log.info("leave.config.policy updated by=%s", getattr(actor, "user_id", None))
    return row


@transaction.atomic
def replace_hierarchy(*, actor, steps: list[dict]) -> list[LeaveHierarchyStep]:
    """BR-EL-019: the configured processing and sanctioning path."""
    authz.require(actor, "leave.policy.update")
    cleaned = []
    for step in steps:
        kind = str(step.get("kind", ""))
        designation = str(step.get("designation", "")).strip()
        if kind not in routing.KINDS:
            raise ConflictError(f"'{kind}' is not a configured step kind.",
                                code="unknown_step_kind")
        if not designation:
            raise ConflictError("Every step needs a designation.",
                                code="designation_required")
        cleaned.append((int(step.get("sequence", 10)), kind, designation,
                        list(step.get("categories", []))))
    if not cleaned:
        raise ConflictError("A hierarchy with no steps decides nothing.",
                            code="hierarchy_empty")
    if not any(kind == routing.FINAL_AUTHORITY for _, kind, _, _ in cleaned):
        raise ConflictError(
            "The hierarchy needs a final sanctioning authority, or higher-sanction "
            "leave cannot be decided.",
            code="hierarchy_incomplete")

    LeaveHierarchyStep.objects.all().delete()
    rows = [LeaveHierarchyStep.objects.create(
        sequence=sequence, kind=kind, designation=designation, categories=categories,
        updated_by_user_id=getattr(actor, "user_id", None))
        for sequence, kind, designation, categories in cleaned]
    log.info("leave.config.hierarchy steps=%d", len(rows))
    return rows


@transaction.atomic
def publish_calendar(*, actor, year: int, days: list[dict],
                     effective_from: date | None = None, label: str = ""
                     ) -> HolidayCalendar:
    """EL-UC-015: publishing is what makes a calendar govern date validation."""
    authz.require(actor, "leave.calendar.publish")
    if not days:
        raise ConflictError("A calendar with no days publishes nothing.",
                            code="calendar_empty")

    version = (HolidayCalendar.objects.filter(year=year)
               .order_by("-version").values_list("version", flat=True).first() or 0) + 1
    calendar = HolidayCalendar.objects.create(
        year=year, version=version, label=label,
        effective_from=effective_from or date(year, 1, 1),
        published_at=timezone.now(),
        published_by_user_id=getattr(actor, "user_id", None),
    )
    for day in days:
        kind = str(day.get("kind", "holiday"))
        if kind not in ("holiday", "restricted"):
            raise ConflictError(f"'{kind}' is not a calendar day kind.",
                                code="unknown_day_kind")
        HolidayCalendarDay.objects.create(
            calendar=calendar, date=day["date"], kind=kind,
            name=str(day.get("name", ""))[:120])
    log.info("leave.config.calendar published year=%s version=%s days=%d", year,
             version, len(days))
    return calendar


@transaction.atomic
def set_threshold(*, actor, task_class: str, reminder_hours: int,
                  escalation_hours: int, escalation_designation: str = ""
                  ) -> SlaThreshold:
    """EL-UC-018 and BR-EL-038: the thresholds the SLA sweep obeys."""
    authz.require(actor, "leave.threshold.update")
    if task_class not in dict(SlaThreshold.TASK_CLASSES):
        raise ConflictError(f"'{task_class}' is not an SLA-controlled task class.",
                            code="unknown_task_class")
    try:
        sla_domain.validate(sla_domain.Thresholds(reminder_hours=reminder_hours,
                                                  escalation_hours=escalation_hours))
    except RuleViolation as exc:
        raise ConflictError(exc.message, code=exc.code) from exc

    row, _ = SlaThreshold.objects.update_or_create(
        task_class=task_class,
        defaults={"reminder_hours": reminder_hours,
                  "escalation_hours": escalation_hours,
                  "escalation_designation": escalation_designation,
                  "updated_by_user_id": getattr(actor, "user_id", None)})
    log.info("leave.config.threshold task=%s reminder=%sh escalation=%sh",
             task_class, reminder_hours, escalation_hours)
    return row


@transaction.atomic
def add_vacation_period(*, actor, start_date: date, end_date: date,
                        label: str = "") -> AcademicVacationPeriod:
    """BR-EL-006: the vacation dates VL validation reads."""
    authz.require(actor, "leave.policy.update")
    if end_date < start_date:
        raise ConflictError("The vacation period ends before it starts.",
                            code="period_invalid")
    return AcademicVacationPeriod.objects.create(
        start_date=start_date, end_date=end_date, label=label,
        recorded_by_user_id=getattr(actor, "user_id", None))
