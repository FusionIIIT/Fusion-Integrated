"""The holiday/RH calendar, and the vacation periods projected into it.

EL-UC-015 has one rule that matters more than the rest: until a REPLACEMENT is
published, the calendar in force keeps governing (BR-EL-031). So a revision is
a new row that stays invisible until it is published, and "effective" is a
question about what is published, never about what is being drafted.

Vacation periods arrive from outside (EXT-01). This module does not own the
Academic Calendar; it keeps a projection of it so VL validation has something
to check against, and `ingest_vacation_periods` is the seam the academic module
would call.
"""
from __future__ import annotations

import logging
from datetime import date

from django.utils import timezone

from core.api.exceptions import NotFoundError, ValidationError
from modules.leave.models import CalendarEntry, LeaveCalendar
from modules.leave.selectors import balances as balance_selectors

log = logging.getLogger("fusion.leave.calendar")

VALID_KINDS = ("closed_holiday", "restricted_holiday", "vacation")


def _validate_entries(entries) -> list[dict]:
    out = []
    for raw in entries:
        kind = raw.get("kind")
        if kind not in VALID_KINDS:
            raise ValidationError(f"{kind or 'That'} is not a calendar entry "
                                  f"type.", code="unknown_entry_kind")
        when = raw.get("date")
        if when is None:
            raise ValidationError("Every entry needs a date.",
                                  code="entry_date_missing")
        ends = raw.get("ends_on") or when
        if ends < when:
            raise ValidationError("A vacation period cannot end before it starts.",
                                  code="entry_period_invalid")
        if kind != "vacation" and ends != when:
            raise ValidationError(
                "A holiday is a single day; only a vacation period spans "
                "several.", code="entry_span_not_allowed")
        out.append({"date": when, "ends_on": ends, "kind": kind,
                    "label": raw.get("label", "")})
    return out


def create_draft(*, principal, year_label: str, label: str,
                 entries) -> LeaveCalendar:
    """A revision. Unpublished, therefore not yet governing anything."""
    calendar = LeaveCalendar.objects.create(
        year_label=year_label, label=label,
        published_by_user_id=principal.user_id)
    replace_entries(calendar=calendar, entries=entries)
    return calendar


def replace_entries(*, calendar: LeaveCalendar, entries) -> None:
    """Swap the whole entry set in one go.

    Partial edits on a calendar are how a holiday quietly stops being one, so
    the API takes the complete set and this replaces it.
    """
    rows = _validate_entries(entries)
    calendar.entries.all().delete()
    CalendarEntry.objects.bulk_create([
        CalendarEntry(calendar=calendar, **row) for row in rows])


def publish(*, principal, calendar_id: int) -> LeaveCalendar:
    """Make a draft effective. The previously published one stops being so the
    moment this is stamped — that is the whole of BR-EL-031."""
    calendar = LeaveCalendar.objects.filter(pk=calendar_id).first()
    if calendar is None:
        raise NotFoundError("No such calendar.", code="not_found")
    if calendar.published_at is not None:
        raise ValidationError("That calendar is already published.",
                              code="already_published")
    calendar.published_at = timezone.now()
    calendar.published_by_user_id = principal.user_id
    calendar.save(update_fields=["published_at", "published_by_user_id",
                                 "updated_at"])
    log.info("leave.calendar.published year=%s by=%s", calendar.year_label,
             principal.user_id)
    return calendar


def ingest_vacation_periods(*, year_label: str,
                            periods) -> int:
    """Project vacation periods from the Academic Calendar into the calendar
    currently in force (EXT-01).

    Called by whoever owns the Academic Calendar; ELM never fetches it itself.
    Idempotent — re-ingesting a period replaces the projection of it.
    """
    calendar = balance_selectors.published_calendar(year_label)
    if calendar is None:
        return 0
    rows = _validate_entries([
        {"date": start, "ends_on": end, "kind": "vacation",
         "label": label or ""} for start, end, label in periods])
    CalendarEntry.objects.filter(calendar=calendar, kind="vacation").delete()
    CalendarEntry.objects.bulk_create([
        CalendarEntry(calendar=calendar, **row) for row in rows])
    return len(rows)


def closed_holidays(year_label: str) -> frozenset[date]:
    return balance_selectors.closed_dates(
        balance_selectors.published_calendar(year_label))


def restricted_holidays(year_label: str) -> frozenset[date]:
    return balance_selectors.restricted_holidays(
        balance_selectors.published_calendar(year_label))
