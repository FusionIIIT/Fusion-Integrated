"""Timetable selectors and slot queries (CFR-DEPT-011, BR-DEPT-010)."""

from __future__ import annotations

from collections.abc import Sequence

from django.db.models import QuerySet

from modules.dept.domain.timetables import TimeSlot
from modules.dept.models.timetable import TimetableEntry


def list_timetables(
    department_code: str,
    program: str | None = None,
    academic_year: int | None = None,
    semester: int | None = None,
) -> QuerySet[TimetableEntry]:
    qs = TimetableEntry.objects.filter(department_id=department_code)
    if program:
        qs = qs.filter(program__iexact=program)
    if academic_year:
        qs = qs.filter(academic_year=academic_year)
    if semester:
        qs = qs.filter(semester=semester)
    return qs.order_by("day_of_week", "start_time")


def get_existing_slots(department_code: str, day_of_week: int) -> Sequence[TimeSlot]:
    """Return existing slots for a given day to check conflicts."""
    entries = TimetableEntry.objects.filter(department_id=department_code, day_of_week=day_of_week)
    return [
        TimeSlot(
            day_of_week=e.day_of_week,
            start_time=e.start_time,
            end_time=e.end_time,
            room_or_lab=e.room_or_lab,
            instructor_id=e.instructor_id,
            entry_id=str(e.id),
        )
        for e in entries
    ]
