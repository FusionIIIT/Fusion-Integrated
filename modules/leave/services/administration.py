"""EL-UC-014..018: configuration, calendars and record maintenance (BR-EL-037)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.directory import contracts as directory
from modules.leave.domain.accounting import Reason
from modules.leave.domain.categories import (
    Category,
    EmployeeKind,
    IneligibleCategory,
    check_eligible,
)
from modules.leave.domain.counting import Half, Interval
from modules.leave.domain.workflow import State
from modules.leave.models import (
    AuthorityRule,
    Holiday,
    HolidayCalendar,
    InstituteOffice,
    LeavePolicy,
    LeaveRequest,
    LeaveTransition,
    OrgUnit,
    SlaPolicy,
    VacationPeriod,
)
from modules.leave.selectors import accounts as reads
from modules.leave.services import accounts
from modules.leave.services.requests import check_no_overlap, period_days


def set_policy(category: Category, annual_days: Decimal, requires_substitute: bool,
               max_days: Decimal | None, by: int) -> LeavePolicy:
    policy, _ = LeavePolicy.objects.update_or_create(category=category.value, defaults={
        "annual_days": annual_days, "requires_substitute": requires_substitute,
        "max_days_per_request": max_days, "updated_by_user_id": by})
    return policy


def save_unit(name: str, head_user_id: int | None, parent_name: str = "") -> OrgUnit:
    parent = None
    if parent_name:
        parent = OrgUnit.objects.filter(name=parent_name).first()
        if parent is None:
            raise NotFoundError(f"There is no unit named {parent_name}.")
        if parent.name == name:
            raise BadRequestError("A unit cannot be its own parent.", code="unit_cycle")
    unit, _ = OrgUnit.objects.update_or_create(
        name=name, defaults={"head_user_id": head_user_id, "parent": parent})
    return unit


def save_authority_rule(category: Category, unit_name: str, applicant_kind: str,
                        sanctioning_user_id: int,
                        establishment_user_id: int | None) -> AuthorityRule:
    unit = OrgUnit.objects.filter(name=unit_name).first() if unit_name else None
    if unit_name and unit is None:
        raise NotFoundError(f"There is no unit named {unit_name}.")
    rule, _ = AuthorityRule.objects.update_or_create(
        category=category.value, unit=unit, applicant_kind=applicant_kind,
        defaults={"sanctioning_user_id": sanctioning_user_id,
                  "establishment_user_id": establishment_user_id})
    return rule


def set_director(user_id: int) -> InstituteOffice:
    office, _ = InstituteOffice.objects.update_or_create(
        code=InstituteOffice.DIRECTOR, defaults={"user_id": user_id})
    return office


def set_sla(state: State, reminder_hours: int, escalation_hours: int,
            escalate_to_user_id: int | None) -> SlaPolicy:
    """BR-EL-038."""
    if escalation_hours <= reminder_hours:
        raise BadRequestError("Escalation must come after the reminder.",
                              code="sla_order")
    sla, _ = SlaPolicy.objects.update_or_create(state=state.value, defaults={
        "reminder_hours": reminder_hours, "escalation_hours": escalation_hours,
        "escalate_to_user_id": escalate_to_user_id})
    return sla


def create_calendar(year: int, title: str, holidays: list[dict], by: int) -> HolidayCalendar:
    """EL-UC-015: a revision is a new draft; publishing replaces the old one."""
    with transaction.atomic():
        cal = HolidayCalendar.objects.create(year=year, title=title, created_by_user_id=by)
        rows = []
        for h in holidays:
            if h["date"].year != year:
                raise BadRequestError(f"{h['date']} is not in {year}.", code="wrong_year")
            rows.append(Holiday(calendar=cal, date=h["date"], name=h["name"], kind=h["kind"]))
        try:
            Holiday.objects.bulk_create(rows)
        except IntegrityError as exc:
            raise BadRequestError("A date is listed twice with the same kind.",
                                  code="duplicate_holiday") from exc
        return cal


def publish_calendar(calendar_id: int, by: int) -> HolidayCalendar:
    """BR-EL-031: the previous published calendar stays effective until this moment."""
    with transaction.atomic():
        cal = HolidayCalendar.objects.select_for_update().filter(pk=calendar_id).first()
        if cal is None:
            raise NotFoundError("That calendar does not exist.")
        if cal.status != HolidayCalendar.DRAFT:
            raise ConflictError("Only a draft calendar can be published.", code="not_draft")
        (HolidayCalendar.objects.select_for_update()
         .filter(year=cal.year, status=HolidayCalendar.PUBLISHED)
         .update(status=HolidayCalendar.SUPERSEDED))
        cal.status, cal.published_at = HolidayCalendar.PUBLISHED, timezone.now()
        cal.published_by_user_id = by
        cal.save()
        return cal


def add_vacation_period(name: str, start: date, end: date) -> VacationPeriod:
    if end < start:
        raise BadRequestError("The vacation cannot end before it starts.", code="invalid_period")
    return VacationPeriod.objects.create(name=name, start_date=start, end_date=end)


def record_offline(by: int, user_id: int, category: Category, start: date, end: date,
                   half: Half, purpose: str, reference: str) -> LeaveRequest:
    """EL-UC-016 / BR-EL-029: synchronises an existing sanction; starts no workflow."""
    if not reference.strip():
        raise BadRequestError("Enter the sanction order or reference number.",
                              code="reference_required")
    user = directory.get_users([user_id]).get(user_id)
    if user is None or user.kind not in (EmployeeKind.FACULTY, EmployeeKind.STAFF):
        raise ConflictError("Offline leave can be recorded for faculty or staff only.",
                            code="not_an_employee")
    kind = EmployeeKind(user.kind)
    try:
        check_eligible(category, kind)
    except IneligibleCategory as exc:
        raise ConflictError(str(exc), code="category_not_eligible") from exc
    with transaction.atomic():
        accounts.lock(user_id)
        days = period_days(category, start, end, half)
        check_no_overlap(user_id, Interval(start, end, half))
        accounts.ensure_annual_credits(user_id, kind, start.year)
        accounts.require_available(user_id, category, start.year, days)
        req = LeaveRequest.objects.create(
            user_id=user_id, category=category.value, start_date=start, end_date=end,
            half=half.value, days=days, purpose=purpose or "Offline sanction",
            status=State.APPROVED.value, decided_at=timezone.now(),
            source=LeaveRequest.OFFLINE, offline_reference=reference.strip())
        LeaveTransition.objects.create(request=req, to_status=State.APPROVED.value,
                                       event="offline_recorded", actor_user_id=by,
                                       note=reference.strip())
        accounts.post(user_id, category, start.year, -days, Reason.OFFLINE, request=req,
                      key=f"debit:{req.pk}", by=by, note=reference)
        return req


def correct_balance(by: int, user_id: int, category: Category, year: int, days: Decimal,
                    note: str) -> None:
    """EL-UC-017: a reversing entry with a reason; never an edit, never a sanction."""
    if days == 0:
        raise BadRequestError("A correction must change the balance.", code="zero_correction")
    if not note.strip():
        raise BadRequestError("State why the balance is being corrected.",
                              code="note_required")
    with transaction.atomic():
        accounts.lock(user_id)
        if reads.balances(user_id, year)[category] + days < 0:
            raise ConflictError("This correction would leave a negative balance.",
                                code="negative_balance")
        accounts.post(user_id, category, year, days, Reason.CORRECTION, by=by, note=note)
