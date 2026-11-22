"""Pure Python timetable conflict detection and validations (BR-DEPT-010, CFR-DEPT-011)."""

from __future__ import annotations

import datetime
from collections.abc import Sequence
from typing import NamedTuple

from modules.dept.domain.exceptions import ConflictError, ValidationError


class TimeSlot(NamedTuple):
    day_of_week: int
    start_time: datetime.time
    end_time: datetime.time
    room_or_lab: str
    instructor_id: str
    entry_id: str | None = None


def do_slots_overlap(
    s1_start: datetime.time,
    s1_end: datetime.time,
    s2_start: datetime.time,
    s2_end: datetime.time,
) -> bool:
    """Return True if two time intervals overlap (strictly before/after does not overlap)."""
    return max(s1_start, s2_start) < min(s1_end, s2_end)


def validate_time_range(start_time: datetime.time, end_time: datetime.time) -> None:
    """Validate that slot start time is strictly before end time."""
    if start_time >= end_time:
        raise ValidationError("Timetable slot start_time must be strictly before end_time.")


def check_slot_conflicts(new_slot: TimeSlot, existing_slots: Sequence[TimeSlot]) -> None:
    """Validate that new slot does not conflict with existing timetable entries."""
    validate_time_range(new_slot.start_time, new_slot.end_time)

    for ex in existing_slots:
        if new_slot.entry_id and ex.entry_id == new_slot.entry_id:
            continue
        if ex.day_of_week != new_slot.day_of_week:
            continue

        if do_slots_overlap(new_slot.start_time, new_slot.end_time, ex.start_time, ex.end_time):
            # Check room conflict
            if ex.room_or_lab.strip().lower() == new_slot.room_or_lab.strip().lower():
                raise ConflictError(
                    f"Room/Lab '{new_slot.room_or_lab}' is already booked on day "
                    f"{new_slot.day_of_week} between {ex.start_time.strftime('%H:%M')} "
                    f"and {ex.end_time.strftime('%H:%M')}."
                )
            # Check instructor conflict
            if ex.instructor_id.strip().lower() == new_slot.instructor_id.strip().lower():
                raise ConflictError(
                    f"Instructor '{new_slot.instructor_id}' is already assigned on day "
                    f"{new_slot.day_of_week} between {ex.start_time.strftime('%H:%M')} "
                    f"and {ex.end_time.strftime('%H:%M')}."
                )
