"""Policy, calendar and offline-sanction recording (EL-UC-014..016)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError
from modules.directory import contracts as directory
from modules.leave.domain.eligibility import LeaveRequest, OccupiedInterval, ValidationError, validate_request
from modules.leave.domain.ledger import OFFLINE
from modules.leave.domain.state_machine import ACTIVE_OCCUPANCY, APPROVED
from modules.leave.models import CalendarEntry, HolidayCalendar, LeaveApplication, LeavePolicy
from modules.leave.services import accounts, policy as policy_svc
from modules.leave.services.authz import require


@transaction.atomic
def publish_policy(actor, *, fields: dict) -> LeavePolicy:
    require(actor, "leave.policy.publish")
    last = LeavePolicy.objects.order_by("-version").first()
    version = (last.version + 1) if last else 1
    LeavePolicy.objects.filter(is_effective=True).update(is_effective=False)
    row = LeavePolicy.objects.create(
        version=version,
        label=fields.get("label") or f"Policy v{version}",
        published_at=timezone.now(),
        published_by_user_id=actor.user_id,
        is_effective=True,
        cl_annual=fields.get("cl_annual", 8),
        rh_annual=fields.get("rh_annual", 2),
        scl_annual=fields.get("scl_annual", 15),
        el_staff_annual=fields.get("el_staff_annual", 30),
        vl_faculty=fields.get("vl_faculty", 60),
        col_annual=fields.get("col_annual", 20),
        vl_to_el_numerator=fields.get("vl_to_el_numerator", 2),
        vl_to_el_denominator=fields.get("vl_to_el_denominator", 1),
        categories_requiring_substitute=fields.get(
            "categories_requiring_substitute", ["SCL", "EL", "COL", "VL"]),
        establishment_step_enabled=fields.get("establishment_step_enabled", True),
        col_requires_medical=fields.get("col_requires_medical", True),
        sla_reminder_hours=fields.get("sla_reminder_hours", 48),
        sla_escalation_hours=fields.get("sla_escalation_hours", 96),
    )
    return row


@transaction.atomic
def publish_calendar(actor, *, year: int, label: str,
                     entries: list[dict]) -> HolidayCalendar:
    require(actor, "leave.calendar.publish")
    last = HolidayCalendar.objects.order_by("-version").first()
    version = (last.version + 1) if last else 1
    HolidayCalendar.objects.filter(is_effective=True).update(is_effective=False)
    cal = HolidayCalendar.objects.create(
        version=version, year=year, label=label or f"Calendar {year} v{version}",
        published_at=timezone.now(), published_by_user_id=actor.user_id,
        is_effective=True,
    )
    for e in entries:
        CalendarEntry.objects.create(
            calendar=cal, kind=e["kind"], start_on=e["start_on"],
            end_on=e["end_on"], label=e.get("label") or "",
        )
    return cal


@transaction.atomic
def record_offline(actor, *, user_id: int, category: str, start_on: date,
                   end_on: date, purpose: str, reference: str,
                   half: str = "", station_leave: bool = False,
                   medical_evidence: bool = False) -> LeaveApplication:
    require(actor, "leave.offline.create")
    if not reference.strip():
        raise ConflictError("Sanction/reference evidence is required.", code="BR-EL-029")
    _, snap = policy_svc.effective_policy()
    calendar = policy_svc.effective_calendar()
    accounts.ensure_year_credits(user_id, start_on.year, snap)
    person = directory.get_users([user_id]).get(user_id)
    kind = (person.kind if person else "staff") or "staff"
    occupied = tuple(
        OccupiedInterval(r.start_on, r.end_on, r.half or None, r.category)
        for r in LeaveApplication.objects.filter(
            user_id=user_id, status__in=ACTIVE_OCCUPANCY)
    )
    req = LeaveRequest(
        category=category, start=start_on, end=end_on, half=half or None,
        station_leave=station_leave, medical_evidence=medical_evidence,
        purpose=purpose, applicant_kind=kind, requires_substitute=False,
    )
    try:
        days = validate_request(
            request=req, policy=snap, calendar=calendar,
            balance=accounts.balance(user_id, category, start_on.year),
            occupied=occupied,
        )
    except ValidationError as exc:
        raise ConflictError(exc.message, code=exc.code) from exc
    app = LeaveApplication.objects.create(
        user_id=user_id, kind="offline", category=category,
        start_on=start_on, end_on=end_on, half=half or "",
        purpose=purpose, chargeable_days=days, station_leave=station_leave,
        medical_evidence=medical_evidence, status=APPROVED,
        unit_code=(person.department if person else "") or "",
        applicant_kind=kind, offline_reference=reference,
        decided_at=timezone.now(), decided_by_user_id=actor.user_id,
    )
    accounts.post(
        user_id=user_id, category=category, year=start_on.year,
        amount=-days, entry_type=OFFLINE,
        memo=f"Offline-sanctioned leave ({reference})", application=app,
    )
    return app
