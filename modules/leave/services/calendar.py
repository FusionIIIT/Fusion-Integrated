"""Calendar reads and configuration (BR-EL-031, CFR-EL-005.2, BR-EL-006).

Only a *published* calendar validates anything; drafts are the clerk's
workbench. Employees read the effective one; admins write versions.
"""
from __future__ import annotations

from datetime import date

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.leave.models import Holiday, HolidayCalendar, VacationPeriod
from modules.leave.services import authz


def effective_calendar() -> HolidayCalendar | None:
    return (HolidayCalendar.objects
            .filter(status=HolidayCalendar.PUBLISHED)
            .order_by("-published_at", "-id")
            .first())


def closed_dates(calendar: HolidayCalendar | None = None) -> set[date]:
    calendar = calendar if calendar is not None else effective_calendar()
    if calendar is None:
        return set()
    return set(calendar.holidays.filter(kind=Holiday.CLOSED)
               .values_list("date", flat=True))


def restricted_dates(calendar: HolidayCalendar | None = None) -> set[date]:
    """The only dates on which an RH request is valid."""
    calendar = calendar if calendar is not None else effective_calendar()
    if calendar is None:
        return set()
    return set(calendar.holidays.filter(kind=Holiday.RESTRICTED)
               .values_list("date", flat=True))


def vacation_windows() -> list[tuple[date, date]]:
    return [(v.start_date, v.end_date)
            for v in VacationPeriod.objects.all()]


@transaction.atomic
def create_calendar(actor, *, title: str, academic_year: str = "",
                    holidays: list[dict] | None = None,
                    publish: bool = False) -> HolidayCalendar:
    authz.require(actor, "leave.calendar.manage")
    calendar = HolidayCalendar.objects.create(
        title=title, academic_year=academic_year)
    Holiday.objects.bulk_create([
        Holiday(calendar=calendar,
                date=date.fromisoformat(str(h["date"])),
                name=h.get("name", ""),
                kind=h.get("kind", Holiday.CLOSED))
        for h in (holidays or [])
    ])
    if publish:
        _publish(calendar, actor)
    return calendar


@transaction.atomic
def publish_calendar(actor, pk: int) -> HolidayCalendar:
    authz.require(actor, "leave.calendar.manage")
    calendar = HolidayCalendar.objects.filter(pk=pk).first()
    if calendar is None:
        raise NotFoundError("Calendar not found.", code="not_found")
    if calendar.status == HolidayCalendar.PUBLISHED:
        raise ConflictError("That calendar is already published.",
                            code="already_published")
    _publish(calendar, actor)
    return calendar


def _publish(calendar: HolidayCalendar, actor) -> None:
    calendar.status = HolidayCalendar.PUBLISHED
    calendar.published_at = timezone.now()
    calendar.published_by_user_id = getattr(actor, "user_id", None)
    calendar.save(update_fields=["status", "published_at",
                                 "published_by_user_id", "updated_at"])


@transaction.atomic
def upsert_vacation(actor, data: dict) -> VacationPeriod:
    authz.require(actor, "leave.calendar.manage")
    start = date.fromisoformat(str(data["start_date"]))
    end = date.fromisoformat(str(data["end_date"]))
    if end < start:
        raise BadRequestError("The vacation period ends before it starts.",
                              code="invalid_interval")
    pk = data.get("id")
    if pk:
        period = VacationPeriod.objects.filter(pk=pk).first()
        if period is None:
            raise NotFoundError("Vacation period not found.", code="not_found")
        for field in ("name", "academic_year", "source_ref"):
            if field in data:
                setattr(period, field, data[field])
        period.start_date, period.end_date = start, end
        period.save()
        return period
    return VacationPeriod.objects.create(
        name=data.get("name", ""), academic_year=data.get("academic_year", ""),
        start_date=start, end_date=end, source_ref=data.get("source_ref", ""))


def calendar_payload() -> dict:
    """What the employee-facing calendar endpoint returns."""
    calendar = effective_calendar()
    vacations = VacationPeriod.objects.all()
    return {
        "calendar": None if calendar is None else {
            "id": calendar.id, "title": calendar.title,
            "academic_year": calendar.academic_year,
            "published_at": calendar.published_at,
        },
        "holidays": ([] if calendar is None else [
            {"date": h.date.isoformat(), "name": h.name, "kind": h.kind}
            for h in calendar.holidays.all()
        ]),
        "vacation_periods": [
            {"id": v.id, "name": v.name, "start_date": v.start_date.isoformat(),
             "end_date": v.end_date.isoformat()}
            for v in vacations
        ],
    }
