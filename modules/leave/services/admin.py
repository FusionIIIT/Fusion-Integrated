"""Leave administration (EL-UC-014, BR-EL-026, BR-EL-029).

Record maintenance is not sanctioning: an administrator may correct an account,
enter an offline-sanctioned record, and manage the hierarchy, but cannot approve
leave. Each function below takes that distinction as given.
"""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError
from modules.leave.services.errors import ValidationError
from modules.leave.domain import categories as cat
from modules.leave.domain import routing as routing_domain
from modules.leave.models import (
    ADJUSTMENT,
    CREDIT,
    DEBIT,
    HierarchyRoute,
    HierarchyRouteStep,
    Holiday,
    HolidayCalendar,
    LeavePolicy,
    OrganizationalUnit,
    SlaThreshold,
    VacationPeriod,
)
from modules.leave.models.calendar import PUBLISHED
from modules.leave.services import authz, calendar, ledger, notifications
from modules.leave.services import leave as leave_service

log = logging.getLogger("fusion.leave.admin")


def read_policy() -> LeavePolicy:
    return LeavePolicy.objects.first() or LeavePolicy()


def update_policy(actor, **changes) -> LeavePolicy:
    """BR-EL-030: one current configuration, edited in place."""
    authz.require(actor, authz.P_BALANCE_UPDATE, authz.P_RECORD_MAINTAIN)
    pol = read_policy()
    allowed = {f.name for f in LeavePolicy._meta.get_fields()
               if hasattr(f, "attname") and not f.auto_created}
    unknown = set(changes) - allowed - {"singleton"}
    if unknown:
        raise ValidationError(
            f"Cannot change {', '.join(sorted(unknown))}.")
    for field, value in changes.items():
        setattr(pol, field, value)
    pol.save()
    log.info("leave.policy.updated fields=%s by=%s", sorted(changes),
             authz.own_id(actor))
    return pol


@transaction.atomic
def adjust_balance(actor, *, user_id: int, year: int, category: str, days: Decimal,
                   note: str, kind: str = ADJUSTMENT) -> None:
    """BR-EL-026: a correction is a visible ledger entry with a reason, never a
    silent edit of the projected figure."""
    authz.require(actor, authz.P_BALANCE_UPDATE)
    if category not in cat.CATEGORIES:
        raise ValidationError(f"Unknown leave type {category!r}.")
    if days <= 0:
        raise ValidationError("Enter a positive number of days.")
    if not note.strip():
        raise ValidationError("Give a reason for the adjustment.")
    if kind not in (CREDIT, DEBIT, ADJUSTMENT):
        raise ValidationError(f"{kind} is not an adjustment kind.")
    ledger.post([ledger.Posting(user_id=user_id, year=year, category=category,
                                kind=kind, days=days, note=note.strip())],
                created_by_user_id=authz.own_id(actor))


def record_offline_leave(actor, *, user_id: int, category: str, start_date: date,
                         end_date: date, sanction_reference: str,
                         purpose: str = "") -> None:
    """BR-EL-029: leave already sanctioned outside the system is posted here, and
    the sanctioning reference is what makes the entry defensible later."""
    authz.require(actor, authz.P_RECORD_MAINTAIN)
    if not sanction_reference.strip():
        raise ValidationError("Record the reference of the sanction that allowed "
                              "this leave.")
    if category not in cat.CATEGORIES:
        raise ValidationError(f"Unknown leave type {category!r}.")
    if start_date > end_date:
        raise ValidationError("The last date cannot be before the first date.")
    days = leave_service.calculate_days(
        category=category, start_date=start_date, end_date=end_date,
        half_day=False)
    ledger.post([ledger.Posting(
        user_id=user_id, year=start_date.year, category=category, kind=DEBIT,
        days=days, note=f"Offline sanctioned leave {start_date}"
                        f"..{end_date} ({sanction_reference.strip()})")],
        created_by_user_id=authz.own_id(actor))
    notifications.enqueue(
        topic="leave.offline_recorded",
        dedupe_key=f"offline:{user_id}:{start_date}:{category}",
        recipient_user_id=user_id,
        subject="Leave recorded on your behalf",
        body=f"{purpose or 'Leave'} from {start_date} to {end_date} was recorded "
             f"under sanction reference {sanction_reference.strip()}.")


def reverse_entry(actor, entry, *, note: str = "") -> None:
    authz.require(actor, authz.P_BALANCE_UPDATE)
    ledger.reverse(entry, note=note, created_by_user_id=authz.own_id(actor))


def reconcile_account(actor, *, user_id: int, year: int) -> list:
    """Rebuild a projected balance from the ledger, for a repair."""
    authz.require(actor, authz.P_BALANCE_UPDATE)
    return ledger.reconcile(user_id, year)


# -- hierarchy ----------------------------------------------------------------

def upsert_unit(actor, *, name: str, head_user_id: int | None) -> OrganizationalUnit:
    authz.require(actor, authz.P_RECORD_MAINTAIN)
    unit = OrganizationalUnit.objects.filter(name__iexact=name.strip()).first()
    if unit is None:
        unit = OrganizationalUnit(name=name.strip())
    unit.head_user_id = head_user_id
    unit.save()
    return unit


def save_route(actor, *, name: str, leave_category: str, org_unit_id: int | None,
               steps: list[dict]) -> HierarchyRoute:
    """BR-EL-018: an ordered chain, and the designation of each step is
    configuration, not a post this module assumes exists."""
    authz.require(actor, authz.P_RECORD_MAINTAIN)
    unit = OrganizationalUnit.objects.filter(pk=org_unit_id).first() \
        if org_unit_id else None
    route, _ = HierarchyRoute.objects.update_or_create(
        name=name, leave_category=leave_category or "",
        org_unit=unit, defaults={"is_active": True})
    route.steps.all().delete()
    for order, step in enumerate(steps, start=1):
        kind = step.get("kind")
        if kind not in routing_domain.STEP_KINDS:
            raise ValidationError(f"{kind!r} is not a routing step kind.")
        HierarchyRouteStep.objects.create(
            route=route, kind=kind, order=step.get("order", order * 10),
            designation=step.get("designation")
            or routing_domain.DEFAULT_DESIGNATIONS.get(kind, ""),
            user_id=step.get("user_id"))
    return route


def save_threshold(actor, *, task_kind: str, reminder_hours: int | None,
                   escalate_hours: int | None, escalation_user_id: int | None,
                   escalation_designation: str = "",
                   escalation_changes_routing: bool = False) -> SlaThreshold:
    authz.require(actor, authz.P_RECORD_MAINTAIN)
    if reminder_hours is not None and escalate_hours is not None:
        if reminder_hours > escalate_hours:
            raise ValidationError("A reminder cannot fall after the escalation.")
    row, _ = SlaThreshold.objects.update_or_create(
        task_kind=task_kind,
        defaults={"reminder_hours": reminder_hours,
                  "escalate_hours": escalate_hours,
                  "escalation_user_id": escalation_user_id,
                  "escalation_designation": escalation_designation,
                  "escalation_changes_routing": escalation_changes_routing,
                  "is_active": True})
    return row


# -- calendar -----------------------------------------------------------------

def save_holiday(actor, *, year: int, date: date, name: str,
                 is_restricted_holiday: bool = False) -> None:
    authz.require(actor, authz.P_RECORD_MAINTAIN)
    cal = HolidayCalendar.objects.filter(year=year).first()
    if cal is None:
        cal = HolidayCalendar.objects.create(year=year)
    Holiday.objects.update_or_create(
        calendar=cal, date=date,
        defaults={"name": name.strip(), "is_restricted_holiday": is_restricted_holiday})


def publish_calendar(actor, *, year: int) -> HolidayCalendar:
    """BR-EL-031: publishing is what makes a calendar the effective one, and it
    displaces the previous effective calendar."""
    authz.require(actor, authz.P_RECORD_MAINTAIN)
    cal = HolidayCalendar.objects.filter(year=year).first()
    if cal is None:
        raise ValidationError(f"There is no holiday calendar for {year}.")
    cal.publish(now=timezone.now())
    return cal


def save_vacation_period(actor, *, label: str, start_date: date, end_date: date,
                         source_reference: str = "") -> VacationPeriod:
    authz.require(actor, authz.P_RECORD_MAINTAIN)
    if start_date > end_date:
        raise ValidationError("The last date cannot be before the first date.")
    period, _ = VacationPeriod.objects.update_or_create(
        label=label, start_date=start_date,
        defaults={"end_date": end_date, "year": start_date.year,
                  "source_reference": source_reference.strip()})
    return period


def calendar_summary(year: int | None = None) -> dict:
    cal = calendar.effective_calendar(year=year)
    return {
        "effective_year": cal.year if cal else None,
        "closed_holidays": sorted(
            cal.holidies.filter(is_restricted_holiday=False)
            .values_list("date", "name")) if cal else [],
        "restricted_holidays": sorted(
            cal.holidays.filter(is_restricted_holiday=True)
            .values_list("date", "name")) if cal else [],
        "vacation_periods": list(
            VacationPeriod.objects.values("label", "start_date", "end_date", "year")),
    }


def unassigned_steps() -> list[str]:
    """Configuration gaps worth surfacing, rather than discovering them when a
    request cannot be routed."""
    gaps: list[str] = []
    for route in HierarchyRoute.objects.filter(is_active=True).prefetch_related("steps"):
        for step in route.steps.all():
            if step.user_id is None:
                gaps.append(f"{route.name}: {step.kind} "
                            f"({step.designation or 'unnamed'}) has no person")
    for unit in OrganizationalUnit.objects.filter(is_active=True,
                                                 head_user_id__isnull=True):
        gaps.append(f"{unit.name} has no Unit Head")
    if gaps:
        log.warning("leave.routing.gaps count=%d", len(gaps))
    return gaps


def ensure_configured(actor) -> None:
    """Refuse administrative work that would create a gap silently."""
    if unassigned_steps():
        raise ConflictError("Some routing steps have nobody assigned. Complete "
                            "the configuration first.")
