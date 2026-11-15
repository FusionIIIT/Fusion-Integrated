"""The effective published configuration (BR-EL-030, BR-EL-031)."""
from __future__ import annotations

from datetime import date

from django.utils import timezone

from modules.elm.domain import counting
from modules.elm.models import CalendarEntry, CalendarVersion, PolicyVersion
from modules.elm.models.config import PUBLISHED


def effective_policy(on: date | None = None) -> PolicyVersion | None:
    on = on or timezone.localdate()
    return (PolicyVersion.objects
            .filter(status=PUBLISHED, effective_from__lte=on)
            .order_by("-effective_from", "-published_at", "-id").first())


def effective_calendar_version(on: date | None = None) -> CalendarVersion | None:
    on = on or timezone.localdate()
    return (CalendarVersion.objects
            .filter(status=PUBLISHED, effective_from__lte=on)
            .order_by("-effective_from", "-published_at", "-id").first())


def calendar_for(version: CalendarVersion | None) -> counting.Calendar:
    if version is None:
        return counting.Calendar()
    closed, restricted, vacations = set(), set(), []
    for e in CalendarEntry.objects.filter(version=version):
        if e.kind == CalendarEntry.VACATION:
            vacations.append((e.start_date, e.end_date))
            continue
        d = e.start_date
        target = closed if e.kind == CalendarEntry.CLOSED_HOLIDAY else restricted
        while d <= e.end_date:
            target.add(d)
            d = date.fromordinal(d.toordinal() + 1)
    return counting.Calendar(frozenset(closed), frozenset(restricted), tuple(vacations))
