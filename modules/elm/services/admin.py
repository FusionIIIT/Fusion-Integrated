"""Administrative writes (EL-UC-014..018). None of these is a sanction (BR-EL-037)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.directory import contracts as directory
from modules.elm.domain import policy
from modules.elm.domain import state_machine as sm
from modules.elm.models import (
    CategoryPolicy,
    Holiday,
    HolidayCalendar,
    LeaveRequest,
    LedgerEntry,
    RequestEvent,
    SanctionRoute,
    SlaPolicy,
    UnitHead,
    VacationPeriod,
)
from modules.elm.selectors import accounts as acc
from modules.elm.services import accounts as ledger
from modules.elm.services.requests import LeaveRuleError, _rule, notify


def _employee_kind(user_id: int) -> str:
    dto = directory.get_users([user_id]).get(user_id)
    if dto is None or dto.kind not in policy.EMPLOYEE_KINDS:
        raise BadRequestError(f"User {user_id} is not a faculty or staff member.",
                              code="not_employee")
    return dto.kind


# -- EL-UC-014 ----------------------------------------------------------------
def set_category_days(category: str, annual_days: Decimal, actor_id: int
                      ) -> CategoryPolicy:
    if category not in policy.CATEGORIES:
        raise BadRequestError("Unknown leave category.", code="unknown_category")
    row, _ = CategoryPolicy.objects.update_or_create(
        category=category,
        defaults={"annual_days": annual_days, "updated_by_id": actor_id})
    return row


def set_unit_head(unit: str, head_user_id: int) -> UnitHead:
    _employee_kind(head_user_id)
    row, _ = UnitHead.objects.update_or_create(
        unit=unit.strip(), defaults={"head_user_id": head_user_id})
    return row


def set_route(category: str, applicant_kind: str, authority_user_id: int,
              establishment_user_id: int | None) -> SanctionRoute:
    if category not in policy.HIGHER_SANCTION:
        raise BadRequestError("Only SCL, EL, COL and VL have a sanctioning path.",
                              code="not_higher_sanction")
    if applicant_kind not in policy.EMPLOYEE_KINDS:
        raise BadRequestError("Kind must be faculty or staff.", code="bad_kind")
    _employee_kind(authority_user_id)
    if establishment_user_id:
        _employee_kind(establishment_user_id)
    row, _ = SanctionRoute.objects.update_or_create(
        category=category, applicant_kind=applicant_kind,
        defaults={"authority_user_id": authority_user_id,
                  "establishment_user_id": establishment_user_id})
    return row


# -- EL-UC-018 ----------------------------------------------------------------
def set_sla(reminder_hours: int, escalation_hours: int,
            escalation_user_id: int | None) -> SlaPolicy:
    if escalation_hours <= reminder_hours:
        raise BadRequestError("Escalation must come after the reminder.",
                              code="bad_sla")
    return SlaPolicy.objects.create(reminder_hours=reminder_hours,
                                    escalation_hours=escalation_hours,
                                    escalation_user_id=escalation_user_id)


# -- EL-UC-015 ----------------------------------------------------------------
@transaction.atomic
def draft_calendar(year: int) -> HolidayCalendar:
    """A revision starts as a copy of the calendar in force (BR-EL-031)."""
    existing = HolidayCalendar.objects.filter(year=year,
                                              status=HolidayCalendar.DRAFT).first()
    if existing:
        return existing
    draft = HolidayCalendar.objects.create(year=year)
    current = acc.published_calendar(year)
    if current:
        Holiday.objects.bulk_create(
            Holiday(calendar=draft, date=h.date, name=h.name, kind=h.kind)
            for h in current.holidays.all())
    return draft


def _draft(calendar_id: int) -> HolidayCalendar:
    cal = HolidayCalendar.objects.filter(pk=calendar_id).first()
    if cal is None:
        raise NotFoundError("That calendar does not exist.")
    if cal.status != HolidayCalendar.DRAFT:
        raise ConflictError("A published calendar is not edited; start a revision.",
                            code="calendar_published")
    return cal


def add_holiday(calendar_id: int, *, on: date, name: str, kind: str) -> Holiday:
    cal = _draft(calendar_id)
    if on.year != cal.year:
        raise BadRequestError(f"The date must be in {cal.year}.", code="wrong_year")
    if kind not in (Holiday.CLOSED, Holiday.RESTRICTED):
        raise BadRequestError("Kind must be closed or restricted.", code="bad_kind")
    try:
        with transaction.atomic():
            return Holiday.objects.create(calendar=cal, date=on, name=name,
                                          kind=kind)
    except IntegrityError as exc:
        raise ConflictError("That holiday is already in the calendar.",
                            code="duplicate_holiday") from exc


def remove_holiday(calendar_id: int, holiday_id: int) -> None:
    cal = _draft(calendar_id)
    deleted, _ = Holiday.objects.filter(calendar=cal, pk=holiday_id).delete()
    if not deleted:
        raise NotFoundError("That holiday does not exist.")


@transaction.atomic
def publish_calendar(calendar_id: int) -> HolidayCalendar:
    cal = _draft(calendar_id)
    cal.status, cal.published_at = HolidayCalendar.PUBLISHED, timezone.now()
    cal.save(update_fields=["status", "published_at", "updated_at"])
    return cal


def add_vacation(label: str, start: date, end: date) -> VacationPeriod:
    if end < start:
        raise BadRequestError("The end date is before the start date.",
                              code="bad_period")
    return VacationPeriod.objects.create(label=label, start_date=start,
                                         end_date=end)


# -- EL-UC-016 ----------------------------------------------------------------
@transaction.atomic
def record_offline(actor_id: int, *, user_id: int, category: str,
                   start_date: date, end_date: date, half: str | None,
                   reference: str, purpose: str = "") -> LeaveRequest:
    """BR-EL-029: synchronise an already-sanctioned leave, no second approval."""
    if not reference.strip():
        raise LeaveRuleError("Record the sanction reference for offline leave.",
                             code="reference_required")
    kind = _employee_kind(user_id)
    _rule(policy.check_category, category, kind)
    _rule(policy.check_period, category, start_date, end_date, half)
    ledger.lock_account(user_id)
    mine = policy.Interval(start_date, end_date, half)
    if any(policy.overlaps(mine, i) for i in acc.active_intervals(user_id)):
        raise LeaveRuleError("This overlaps leave already on the employee's record.",
                             code="overlap")
    days = policy.count_days(category, start_date, end_date, half,
                             acc.holiday_dates(start_date, end_date, "closed"))
    _rule(policy.check_counted, days)
    _rule(policy.check_balance, days,
          ledger.available(user_id, kind, category, start_date.year))
    req = LeaveRequest.objects.create(
        user_id=user_id, kind=LeaveRequest.LEAVE, source=LeaveRequest.OFFLINE,
        category=category, applicant_kind=kind, start_date=start_date,
        end_date=end_date, half=half or "", days=days, purpose=purpose,
        state=sm.APPROVED, offline_reference=reference.strip()[:200],
        decided_by_id=actor_id, decided_at=timezone.now())
    RequestEvent.objects.create(request=req, actor_id=actor_id,
                                actor_role="leave_administrator",
                                to_state=sm.APPROVED,
                                note=f"Offline sanction {reference}"[:500])
    ledger.post(user_id=user_id, category=category, on=start_date,
                kind=LedgerEntry.DEBIT, days=-days, request=req,
                recorded_by_id=actor_id, note="Offline-sanctioned leave")
    notify(user_id, f"Offline-sanctioned {category} leave was recorded.", req)
    return req


# -- EL-UC-017 ----------------------------------------------------------------
@transaction.atomic
def adjust_balance(actor_id: int, *, user_id: int, category: str, year: int,
                   days: Decimal, note: str) -> LedgerEntry:
    """A correcting entry; past rows are never edited."""
    if category not in policy.CATEGORIES:
        raise BadRequestError("Unknown leave category.", code="unknown_category")
    if not note.strip():
        raise BadRequestError("Say why the record is being corrected.",
                              code="note_required")
    _employee_kind(user_id)
    ledger.lock_account(user_id)
    if acc.balances(user_id, year)[category] + days < 0:
        raise LeaveRuleError("This correction would make the balance negative.",
                             code="negative_balance")
    return ledger.post(user_id=user_id, category=category, on=date(year, 1, 1),
                       kind=LedgerEntry.ADJUSTMENT, days=days, note=note,
                       recorded_by_id=actor_id)
