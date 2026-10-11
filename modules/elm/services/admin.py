"""ELM configuration maintenance (EL-UC-014/015/018).

Policy parameters, the sanctioning hierarchy, the
holiday/RH calendar, organizational units and their
Unit Heads, the vacation-period projection, and the
SLA thresholds. None of this drafts or publishes
except the calendar, which is published to become
effective (BR-EL-031).
"""
from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError
from modules.elm.models import (
    HierarchyConfig,
    Holiday,
    HolidayCalendar,
    OrgUnit,
    PolicyConfig,
    SlaConfig,
    VacationPeriod,
)
from modules.elm.services import authz
from modules.elm.services import policy as policy_service

log = logging.getLogger("fusion.elm.admin")


# -- policy parameters (BR-EL-030) ------------------------------


def get_policy() -> PolicyConfig:
    return policy_service.current_policy()


@transaction.atomic
def update_policy(principal, *, entitlements=None,
                    director_designations=None,
                    establishment_designations=None,
                    year_end_month_day=None,
                    station_leave_enabled=None,
                    medical_evidence_required=None,
                    ) -> PolicyConfig:
    """Replace the current policy parameters.

    There is no versioning: the row *is* the current
    configuration, and the change applies to requests
    submitted from the next moment.
    """
    authz.require_permission(principal, "elm.config.policy")
    policy = policy_service.current_policy()
    if entitlements is not None:
        policy.entitlements = entitlements
    if director_designations is not None:
        policy.director_designations = list(
            director_designations)
    if establishment_designations is not None:
        policy.establishment_designations = list(
            establishment_designations)
    if year_end_month_day is not None:
        policy.year_end_month_day = year_end_month_day
    if station_leave_enabled is not None:
        policy.station_leave_enabled = station_leave_enabled
    if medical_evidence_required is not None:
        policy.medical_evidence_required = (
            medical_evidence_required)
    policy.save()
    return policy


# -- hierarchy configuration (BR-EL-016…020) --------------------


def hierarchy_rows():
    return HierarchyConfig.objects.all()


@transaction.atomic
def upsert_hierarchy(principal, *, category_group: str,
                         unit_type: str,
                         establishment_required: bool,
                         sanctioning_authority: str,
                         ) -> HierarchyConfig:
    """Configure the sanctioning path for one
    (category group, unit type) pair."""
    authz.require_permission(principal, "elm.config.hierarchy")
    row, _ = HierarchyConfig.objects.update_or_create(
        category_group=category_group, unit_type=unit_type,
        defaults={
            "establishment_required":
                establishment_required,
            "sanctioning_authority": sanctioning_authority,
        })
    return row


# -- SLA thresholds (EL-UC-021) ------------------------------------


def sla_rows():
    return SlaConfig.objects.all()


@transaction.atomic
def upsert_sla(principal, *, task_class: str,
                 reminder_hours: int,
                 escalation_hours: int,
                 escalation_action: str = "notify",
                 escalation_target_role: str = "",
                 ) -> SlaConfig:
    """Configure reminder/escalation thresholds for one
    workflow task class."""
    authz.require_permission(principal, "elm.config.sla")
    if escalation_hours < reminder_hours:
        raise ConflictError(
            "Escalation must follow the reminder.",
            code="sla_threshold_order")
    row, _ = SlaConfig.objects.update_or_create(
        task_class=task_class,
        defaults={
            "reminder_hours": reminder_hours,
            "escalation_hours": escalation_hours,
            "escalation_action": escalation_action,
            "escalation_target_role":
                escalation_target_role,
        })
    return row


# -- holiday / RH calendar (BR-EL-031) -----------------------------


def calendar_list():
    return HolidayCalendar.objects.all()


def effective_calendar():
    from modules.elm.selectors.requests import effective_calendar as _effective

    return _effective()


@transaction.atomic
def create_calendar(principal, *, name: str, year: int,
                      description: str = "",
                      ) -> HolidayCalendar:
    """Create a draft calendar. It governs nothing until
    it is published."""
    authz.require_permission(principal, "elm.config.calendar")
    if HolidayCalendar.objects.filter(
            name=name, year=year).exists():
        raise ConflictError(
            "A calendar with that name and year already "
            "exists.", code="calendar_exists")
    return HolidayCalendar.objects.create(
        name=name, year=year, description=description)


@transaction.atomic
def upsert_holiday(principal, *, calendar_id: int, date,
                     label: str, kind: str,
                     closed: bool = True) -> Holiday:
    """Add or revise a day in a *draft* calendar.

    A published calendar is immutable — revising it
    means publishing a replacement (BR-EL-031).
    """
    authz.require_permission(principal, "elm.config.calendar")
    calendar = HolidayCalendar.objects.get(id=calendar_id)
    if calendar.published_at is not None:
        raise ConflictError(
            "A published calendar cannot be revised; "
            "publish a replacement instead.",
            code="calendar_published")
    holiday, _ = Holiday.objects.update_or_create(
        calendar=calendar, date=date,
        defaults={"label": label, "kind": kind,
                  "closed": closed})
    return holiday


@transaction.atomic
def publish_calendar(principal, calendar_id: int,
                       ) -> HolidayCalendar:
    """Publish a draft calendar.

    The published calendar becomes the currently
    effective one and stays effective until a
    replacement is published.
    """
    authz.require_permission(principal, "elm.config.calendar")
    calendar = HolidayCalendar.objects.get(id=calendar_id)
    if calendar.published_at is not None:
        raise ConflictError(
            "This calendar is already published.",
            code="calendar_published")
    if not calendar.holidays.exists():
        raise ConflictError(
            "A calendar with no days cannot be "
            "published.", code="calendar_empty")
    calendar.published_at = timezone.now()
    calendar.save(update_fields=["published_at"])
    return calendar


# -- organizational units and Unit Heads (PS §1) ------------------


def unit_list():
    return OrgUnit.objects.all()


@transaction.atomic
def upsert_unit(principal, *, code: str, name: str,
                  unit_type: str) -> OrgUnit:
    """Create or revise an organizational unit."""
    authz.require_permission(principal, "elm.config.units")
    unit, _ = OrgUnit.objects.update_or_create(
        code=code,
        defaults={"name": name, "unit_type": unit_type})
    return unit


@transaction.atomic
def set_unit_head(principal, *, code: str,
                    head_user_id: int | None,
                    ) -> OrgUnit:
    """Appoint (or clear) the Unit Head of a unit.

    The Unit Head is configuration, not a designation
    inference: whoever is appointed here reviews the
    unit's leave requests.
    """
    authz.require_permission(principal, "elm.config.units")
    unit = OrgUnit.objects.get(code=code)
    unit.head_user_id = head_user_id
    unit.save(update_fields=["head_user_id"])
    return unit


# -- employee profiles ----------------------------------------------


@transaction.atomic
def set_employee_profile(principal, *, user_id: int,
                           employee_kind: str,
                           designation_name: str,
                           unit_code: str | None,
                           ) -> None:
    """Maintain the ELM projection of an employee:
    kind, designation and organizational unit.

    Routing reads these rows, so this is how a new
    employee becomes routable.
    """
    authz.require_permission(principal, "elm.config.units")
    from modules.elm.models import EmployeeProfile

    if unit_code is not None and not OrgUnit.objects.filter(
            code=unit_code).exists():
        raise ConflictError(
            f"Unknown organizational unit {unit_code!r}.",
            code="unknown_unit")
    EmployeeProfile.objects.update_or_create(
        user_id=user_id,
        defaults={
            "employee_kind": employee_kind,
            "designation_name": designation_name,
            "unit_code_id": unit_code,
            "is_active": True,
        })


# -- vacation-period projection (BR-EL-006) ------------------------

@transaction.atomic
def maintain_record(principal, *, record_id: int,
                        status: str = "",
                        actual_end_date=None,
                        reason: str = ""):
    """Authorized maintenance of a leave record.

    The Leave Administrator may close out an
    ongoing record (marking it completed, with its
    actual end date) when no resumption was
    submitted — for example a record entered
    before ELM tracked resumptions. Every change
    lands in the audit trail; sanctioning itself
    stays on the workflow path (BR-EL-037).
    """
    authz.require_permission(principal, "elm.records.maintain")
    from modules.elm.models import LeaveRecord, RequestEvent

    record = LeaveRecord.objects.get(id=record_id)
    changed = {}
    if status:
        if status not in ("ongoing", "completed"):
            raise ConflictError(
                "Maintained status must be ongoing "
                "or completed.", code="invalid_status")
        if record.status != status:
            record.status = status
            changed["status"] = status
    if actual_end_date is not None and (
            record.actual_end_date != actual_end_date):
        record.actual_end_date = actual_end_date
        changed["actual_end_date"] = str(actual_end_date)
    if not changed:
        return record, changed
    record.save()
    RequestEvent.objects.create(
        request=record.source_request,
        event="state_change",
        outcome="record_maintained",
        actor_user_id=principal.user_id,
        actor_label=authz.user_label(principal),
        reason=reason,
        payload={"record_id": record.id,
                 **changed},
    )
    return record, changed


def vacation_list():
    return VacationPeriod.objects.all()


@transaction.atomic
def upsert_vacation(principal, *, label: str,
                      start_date, end_date,
                      academic_year: str = "",
                      ) -> VacationPeriod:
    """Maintain the Academic Calendar vacation
    projection that VL applicability is checked
    against.

    The authoritative calendar is maintained by the
    institute Academic Calendar system outside ELM;
    this is the projection ELM reads (EXT-01).
    """
    authz.require_permission(principal, "elm.config.vacation")
    if end_date < start_date:
        raise ConflictError(
            "The vacation period ends before it starts.",
            code="invalid_period")
    period, _ = VacationPeriod.objects.update_or_create(
        label=label, start_date=start_date,
        defaults={"end_date": end_date,
                  "academic_year": academic_year})
    return period
