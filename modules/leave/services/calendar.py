"""The holiday/RH calendar: draft, revise, publish (EL-UC-015, BR-EL-031); and vacation periods."""
from __future__ import annotations

from collections.abc import Iterable

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.leave.models import Holiday, HolidayCalendar, VacationPeriod
from modules.leave.services import authz


@transaction.atomic
def start_draft(*, actor, year: int) -> HolidayCalendar:
    """A new draft, prefilled from the published calendar so a revision starts from what governs."""
    authz.require(actor, "leave.calendar.update")
    if not 2000 <= year <= 2100:
        raise ConflictError("Choose a calendar year between 2000 and 2100.", code="invalid_year")
    if HolidayCalendar.objects.filter(year=year, status=HolidayCalendar.DRAFT).exists():
        raise ConflictError(f"A draft for {year} already exists; edit or publish it.",
                            code="draft_exists")
    version = (HolidayCalendar.objects.filter(year=year).aggregate(v=Max("version"))["v"]
               or 0) + 1
    draft = HolidayCalendar.objects.create(year=year, version=version,
                                           created_by_user_id=actor.user_id)
    current = HolidayCalendar.objects.filter(year=year, status=HolidayCalendar.PUBLISHED).first()
    if current is not None:
        Holiday.objects.bulk_create([Holiday(calendar=draft, date=h.date, name=h.name, kind=h.kind)
                                     for h in current.holidays.all()])
    return draft


def _draft(calendar_id: int) -> HolidayCalendar:
    cal = HolidayCalendar.objects.select_for_update().filter(pk=calendar_id).first()
    if cal is None:
        raise NotFoundError("No such calendar.")
    if cal.status != HolidayCalendar.DRAFT:
        raise ConflictError("A published calendar is never edited. Start a new draft to "
                            "replace it.", code="calendar_not_draft")
    return cal


@transaction.atomic
def replace_entries(*, actor, calendar_id: int, entries: Iterable[dict]) -> HolidayCalendar:
    authz.require(actor, "leave.calendar.update")
    cal = _draft(calendar_id)
    rows, seen, problems = [], set(), []
    for e in entries:
        d, name, kind = e["date"], (e.get("name") or "").strip(), e.get("kind")
        if d.year != cal.year:
            problems.append(f"{d} is not in {cal.year}.")
        if d in seen:
            problems.append(f"{d} appears twice.")
        if not name:
            problems.append(f"{d} needs a name.")
        if kind not in (Holiday.CLOSED, Holiday.RESTRICTED):
            problems.append(f"{d}: the kind must be closed or restricted.")
        seen.add(d)
        rows.append(Holiday(calendar=cal, date=d, name=name[:120], kind=kind))
    if problems:
        raise ConflictError("The calendar was not saved.", code="calendar_invalid",
                            details=[{"message": p} for p in problems])
    cal.holidays.all().delete()
    Holiday.objects.bulk_create(rows)
    cal.save(update_fields=["updated_at"])
    return cal


@transaction.atomic
def publish(*, actor, calendar_id: int) -> HolidayCalendar:
    """The replacement governs from this commit; the old one is kept, superseded."""
    authz.require(actor, "leave.calendar.publish")
    cal = _draft(calendar_id)
    if not cal.holidays.exists():
        raise ConflictError("An empty calendar cannot be published.", code="calendar_empty")
    HolidayCalendar.objects.select_for_update().filter(
        year=cal.year, status=HolidayCalendar.PUBLISHED).update(
        status=HolidayCalendar.SUPERSEDED, updated_at=timezone.now())
    cal.status, cal.published_at, cal.published_by_user_id = (
        HolidayCalendar.PUBLISHED, timezone.now(), actor.user_id)
    cal.save(update_fields=["status", "published_at", "published_by_user_id", "updated_at"])
    return cal


@transaction.atomic
def add_vacation(*, actor, label: str, start_date, end_date,
                 source_reference: str = "") -> VacationPeriod:
    authz.require(actor, "leave.calendar.update")
    if end_date < start_date or not label.strip():
        raise ConflictError("A vacation period needs a name and must not end before it starts.",
                            code="vacation_invalid")
    if VacationPeriod.objects.filter(start_date__lte=end_date, end_date__gte=start_date).exists():
        raise ConflictError("This overlaps a vacation period already entered.",
                            code="vacation_overlaps")
    return VacationPeriod.objects.create(label=label.strip()[:120], start_date=start_date,
                                         end_date=end_date,
                                         source_reference=source_reference.strip()[:200],
                                         created_by_user_id=actor.user_id)


@transaction.atomic
def remove_vacation(*, actor, vacation_id: int) -> None:
    authz.require(actor, "leave.calendar.update")
    deleted, _ = VacationPeriod.objects.filter(pk=vacation_id).delete()
    if not deleted:
        raise NotFoundError("No such vacation period.")
