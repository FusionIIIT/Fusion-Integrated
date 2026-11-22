"""PHC services: schedule management and attendance marking.

PHC-UC-07, PHC-UC-08, PHC-UC-22.
AFR-PHC-001 … AFR-PHC-005.
"""

from __future__ import annotations

import logging

from core.api.exceptions import BadRequestError
from modules.phc.models import DoctorAttendance, DoctorSchedule

log = logging.getLogger("fusion.phc.schedules")


def create_schedule_slot(
    *,
    doctor_name: str,
    specialisation: str = "",
    day_of_week: str,
    start_time,
    end_time,
    room: str = "",
    is_published: bool = False,
    actor_user_id: int,
) -> DoctorSchedule:
    """PHC-UC-07/22, AFR-PHC-002: Create a master schedule slot."""
    if start_time >= end_time:
        raise BadRequestError("start_time must be before end_time.")
    slot = DoctorSchedule.objects.create(
        doctor_name=doctor_name,
        specialisation=specialisation,
        day_of_week=day_of_week,
        start_time=start_time,
        end_time=end_time,
        room=room,
        is_published=is_published,
        created_by_user_id=actor_user_id,
    )
    log.info("phc.schedule.created slot=%s dr=%s by=%s", slot.pk, doctor_name, actor_user_id)
    return slot


def publish_schedule(*, slot: DoctorSchedule, actor_user_id: int) -> DoctorSchedule:
    """PHC-UC-07/22, AFR-PHC-003: Publish a schedule slot to patients."""
    slot.is_published = True
    slot.save(update_fields=["is_published", "updated_at"])
    log.info("phc.schedule.published slot=%s by=%s", slot.pk, actor_user_id)
    return slot


def mark_attendance(
    *,
    schedule: DoctorSchedule,
    status: str,
    date,
    actor_user_id: int,
) -> DoctorAttendance:
    """PHC-UC-08, AFR-PHC-004: Mark a doctor available or departed for today."""
    valid_statuses = {"available", "departed"}
    if status not in valid_statuses:
        raise BadRequestError(f"status must be one of {valid_statuses}.")

    attendance, _ = DoctorAttendance.objects.update_or_create(
        schedule=schedule,
        date=date,
        defaults={
            "status": status,
            "marked_by_user_id": actor_user_id,
        },
    )
    log.info(
        "phc.attendance.marked slot=%s date=%s status=%s by=%s",
        schedule.pk,
        date,
        status,
        actor_user_id,
    )
    return attendance
