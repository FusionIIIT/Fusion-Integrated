"""Configuration ELM reads while validating and routing (EL-UC-014/015/018).

Three separate capabilities, one gate, and one shared property: all of them
change *current* values, not a version. BR-EL-030 removed the policy
draft/publish/effective lifecycle, so there is nothing here that creates an
unpublished policy version — an administrator edits the current row and the
next validation uses it.

The holiday/RH calendar is the exception the baseline keeps: a calendar only
governs once it is *published*, and until a replacement is published the
current one remains effective (BR-EL-031).
"""
from __future__ import annotations

import logging
from datetime import date

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError
from modules.leave.domain import categories as cat
from modules.leave.models import (
    HierarchyStep,
    HolidayCalendar,
    HolidayEntry,
    LeavePolicy,
    SlaThreshold,
)

log = logging.getLogger("fusion.leave.config")

#: EL-UC-014/015/018 — configuration is the Leave Administrator's capability.
P_CONFIGURE = "leave.type.manage"

VALID_KINDS = {"closed_holiday", "restricted_holiday"}
VALID_STEPS = {"unit_head", "establishment", "sanction"}


# -- Policy (EL-UC-014) --------------------------------------------------------
@transaction.atomic
def save_policy(*, actor, leave_year: int, entitlements: dict | None = None,
                label: str = "", continuous_counting: list | None = None,
                half_day_categories: list | None = None,
                year_end_month: int | None = None,
                year_end_day: int | None = None,
                scl_admissibility_note: str | None = None) -> LeavePolicy:
    """Create or revise the current policy for a leave year.

    Unknown category codes are refused rather than stored: a typo in an
    entitlement key would silently leave the real category on its default.
    """
    from modules.leave.services import authz

    authz.require(actor, P_CONFIGURE)

    table = {k: str(v) for k, v in (entitlements or cat.ENTITLEMENT).items()}
    unknown = sorted(set(table) - set(cat.CATEGORIES))
    if unknown:
        raise ConflictError(
            f"Unknown leave categor{'y' if len(unknown) == 1 else 'ies'}: "
            f"{', '.join(unknown)}.", code="unknown_category",
            details=[{"supported": list(cat.CATEGORIES)}])
    for key, value in table.items():
        if float(value) < 0:
            raise ConflictError(f"The entitlement for {key} cannot be negative.",
                                code="invalid_entitlement")
    if year_end_month is not None and not 1 <= int(year_end_month) <= 12:
        raise ConflictError("The year-end month must be between 1 and 12.",
                            code="invalid_year_end")

    policy, created = LeavePolicy.objects.get_or_create(leave_year=leave_year)
    policy.label = (label or policy.label or f"Leave policy {leave_year}")[:60]
    policy.entitlements = table
    policy.continuous_counting = sorted(continuous_counting
                                        or cat.CONTINUOUS_COUNTING)
    policy.half_day_categories = sorted(half_day_categories
                                        or cat.HALF_DAY_CATEGORIES)
    policy.is_current = True
    if year_end_month is not None:
        policy.year_end_month = int(year_end_month)
    if year_end_day is not None:
        policy.year_end_day = int(year_end_day)
    if scl_admissibility_note is not None:
        policy.scl_admissibility_note = scl_admissibility_note[:300]
    policy.save()
    if created:
        # One current policy at a time: later years supersede earlier ones.
        (LeavePolicy.objects.exclude(pk=policy.pk).filter(is_current=True)
         .update(is_current=False))
    log.info("leave.config.policy_saved year=%s by=%s", leave_year,
             getattr(actor, "user_id", None))
    return policy


# -- Hierarchy (EL-UC-014) -----------------------------------------------------
@transaction.atomic
def replace_hierarchy(*, actor, category: str, steps: list[dict]) -> list[HierarchyStep]:
    """Replace the configured path for one category with the supplied steps."""
    from modules.leave.services import authz

    authz.require(actor, P_CONFIGURE)
    if category and category not in cat.CATEGORIES:
        raise ConflictError(f"{category!r} is not a leave category in this baseline.",
                            code="unsupported_category")
    for index, step in enumerate(steps, start=1):
        if step.get("step_kind") not in VALID_STEPS:
            raise ConflictError(
                f"Step {index} has an unknown kind {step.get('step_kind')!r}.",
                code="invalid_step_kind",
                details=[{"valid": sorted(VALID_STEPS)}])

    HierarchyStep.objects.filter(category=category).delete()
    created = [
        HierarchyStep.objects.create(
            category=category, unit=(step.get("unit") or "")[:60],
            designation=(step.get("designation") or "")[:80],
            step_order=int(step.get("step_order", index)),
            step_kind=step["step_kind"],
            authority=(step.get("authority") or "")[:32],
            label=(step.get("label") or "")[:80])
        for index, step in enumerate(steps, start=1)
    ]
    log.info("leave.config.hierarchy_replaced category=%s steps=%d by=%s",
             category or "any", len(created), getattr(actor, "user_id", None))
    return created


# -- Holiday/RH calendar (EL-UC-015) -------------------------------------------
@transaction.atomic
def save_calendar(*, actor, leave_year: int, entries: list[dict],
                  label: str = "") -> HolidayCalendar:
    """Create or revise an *unpublished* calendar.

    Revising a published calendar replaces its entries but leaves it
    unpublished until `publish_calendar` runs, so a half-finished edit never
    becomes the governing calendar.
    """
    from modules.leave.services import authz

    authz.require(actor, P_CONFIGURE)
    for index, entry in enumerate(entries, start=1):
        if entry.get("kind") not in VALID_KINDS:
            raise ConflictError(
                f"Entry {index} has an unknown kind {entry.get('kind')!r}.",
                code="invalid_holiday_kind", details=[{"valid": sorted(VALID_KINDS)}])

    calendar = (HolidayCalendar.objects.filter(leave_year=leave_year,
                                               published_at__isnull=True)
                .order_by("-id").first()
                or HolidayCalendar.objects.create(
                    leave_year=leave_year,
                    label=(label or f"Calendar {leave_year}")[:80]))
    if label:
        calendar.label = label[:80]
        calendar.save(update_fields=["label", "updated_at"])

    calendar.entries.all().delete()
    HolidayEntry.objects.bulk_create([
        HolidayEntry(calendar=calendar,
                     date=_as_date(entry["date"]),
                     kind=entry["kind"],
                     label=(entry.get("label") or "")[:120])
        for entry in entries
    ])
    log.info("leave.config.calendar_saved year=%s entries=%d by=%s", leave_year,
             len(entries), getattr(actor, "user_id", None))
    return calendar


@transaction.atomic
def publish_calendar(*, actor, calendar_id: int) -> HolidayCalendar:
    """Publishing makes this calendar the effective one, and no other."""
    from modules.leave.services import authz

    authz.require(actor, P_CONFIGURE)
    calendar = HolidayCalendar.objects.select_for_update().filter(
        pk=calendar_id).first()
    if calendar is None:
        raise ConflictError("No such holiday calendar.", code="not_found")
    HolidayCalendar.objects.filter(leave_year=calendar.leave_year,
                                   is_effective=True).exclude(
        pk=calendar.pk).update(is_effective=False)
    calendar.is_effective = True
    calendar.published_at = timezone.now()
    calendar.published_by_user_id = getattr(actor, "user_id", None)
    calendar.save(update_fields=["is_effective", "published_at",
                                 "published_by_user_id", "updated_at"])
    log.info("leave.config.calendar_published year=%s by=%s", calendar.leave_year,
             getattr(actor, "user_id", None))
    return calendar


# -- SLA thresholds (EL-UC-018) ------------------------------------------------
@transaction.atomic
def save_thresholds(*, actor, task_class: str, reminder_hours: int,
                    escalation_hours: int, escalation_action: str = "notify",
                    escalate_to_role: str = "") -> SlaThreshold:
    """Configure the reminder and escalation thresholds for a task class."""
    from modules.leave.services import authz

    authz.require(actor, P_CONFIGURE)
    if not (task_class or "").strip():
        raise ConflictError("An SLA threshold needs a task class.",
                            code="task_class_required")
    if escalation_hours < reminder_hours:
        raise ConflictError(
            "The escalation threshold cannot be earlier than the reminder.",
            code="escalation_before_reminder")
    if escalation_action == "reassign" and not (escalate_to_role or "").strip():
        raise ConflictError(
            "A routing-changing escalation must name the role it reassigns to.",
            code="escalation_target_required")

    threshold, _ = SlaThreshold.objects.update_or_create(
        task_class=task_class[:40],
        defaults={"reminder_hours": int(reminder_hours),
                  "escalation_hours": int(escalation_hours),
                  "escalation_action": escalation_action,
                  "escalate_to_role": escalate_to_role[:80],
                  "is_active": True})
    log.info("leave.config.sla_saved task_class=%s by=%s", task_class,
             getattr(actor, "user_id", None))
    return threshold


def _as_date(value) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))
