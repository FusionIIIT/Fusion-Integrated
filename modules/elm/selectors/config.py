"""Effective published policy and calendar selectors (BR-EL-030, BR-EL-031)."""
from __future__ import annotations

from datetime import date

from django.utils import timezone

from modules.elm.domain.counting import Calendar
from modules.elm.domain.policy import Policy, parse
from modules.elm.models import CalendarEntry, CalendarVersion, PolicyVersion
from modules.elm.models.config import PUBLISHED


def effective_policy_version(on: date | None = None) -> PolicyVersion | None:
    d = on or timezone.localdate()
    return (
        PolicyVersion.objects.filter(status=PUBLISHED, effective_from__lte=d)
        .order_by("-effective_from", "-id")
        .first()
    )


def effective_policy(on: date | None = None) -> tuple[PolicyVersion | None, Policy | None]:
    pv = effective_policy_version(on)
    if pv is None:
        return None, None
    return pv, parse(pv.params)


def effective_calendar_version(on: date | None = None) -> CalendarVersion | None:
    d = on or timezone.localdate()
    return (
        CalendarVersion.objects.filter(status=PUBLISHED, effective_from__lte=d)
        .order_by("-effective_from", "-id")
        .first()
    )


def effective_calendar(on: date | None = None) -> Calendar:
    cv = effective_calendar_version(on)
    if cv is None:
        return Calendar()
    closed = set()
    rh = set()
    vacations = []
    for entry in cv.entries.all():
        if entry.kind == CalendarEntry.CLOSED_HOLIDAY:
            cur = entry.start_date
            while cur <= entry.end_date:
                closed.add(cur)
                from datetime import timedelta
                cur += timedelta(days=1)
        elif entry.kind == CalendarEntry.RESTRICTED_HOLIDAY:
            cur = entry.start_date
            while cur <= entry.end_date:
                rh.add(cur)
                from datetime import timedelta
                cur += timedelta(days=1)
        elif entry.kind == CalendarEntry.VACATION:
            vacations.append((entry.start_date, entry.end_date))
    return Calendar(
        closed_holidays=frozenset(closed),
        restricted_holidays=frozenset(rh),
        vacations=tuple(vacations),
    )
