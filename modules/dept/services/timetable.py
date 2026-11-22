"""Timetable management service with conflict enforcement (CFR-DEPT-011, BR-DEPT-010)."""

from __future__ import annotations

import datetime

from modules.dept.domain.timetables import TimeSlot, check_slot_conflicts
from modules.dept.models.department import Department
from modules.dept.models.timetable import TimetableEntry
from modules.dept.selectors.timetable import get_existing_slots


def save_timetable_entry(
    department_code: str,
    program: str,
    academic_year: int,
    semester: int,
    day_of_week: int,
    start_time: datetime.time,
    end_time: datetime.time,
    course_code: str,
    course_name: str,
    instructor_id: str,
    room_or_lab: str,
    entry_id: str | None = None,
) -> TimetableEntry:
    slot = TimeSlot(
        day_of_week=day_of_week,
        start_time=start_time,
        end_time=end_time,
        room_or_lab=room_or_lab.strip(),
        instructor_id=instructor_id.strip(),
        entry_id=entry_id,
    )
    existing_slots = get_existing_slots(department_code, day_of_week)
    check_slot_conflicts(slot, existing_slots)

    dept, _ = Department.objects.get_or_create(
        code=department_code,
        defaults={"name": f"Department of {department_code}"},
    )

    if entry_id:
        entry = TimetableEntry.objects.get(id=entry_id, department=dept)
        entry.program = program.strip()
        entry.academic_year = academic_year
        entry.semester = semester
        entry.day_of_week = day_of_week
        entry.start_time = start_time
        entry.end_time = end_time
        entry.course_code = course_code.strip()
        entry.course_name = course_name.strip()
        entry.instructor_id = instructor_id.strip()
        entry.room_or_lab = room_or_lab.strip()
        entry.save()
        return entry

    return TimetableEntry.objects.create(
        department=dept,
        program=program.strip(),
        academic_year=academic_year,
        semester=semester,
        day_of_week=day_of_week,
        start_time=start_time,
        end_time=end_time,
        course_code=course_code.strip(),
        course_name=course_name.strip(),
        instructor_id=instructor_id.strip(),
        room_or_lab=room_or_lab.strip(),
    )


def delete_timetable_entry(entry_id: str) -> None:
    TimetableEntry.objects.filter(id=entry_id).delete()
