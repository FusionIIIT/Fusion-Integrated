"""Doctor schedules and attendance (PHC-UC-07, PHC-UC-08, PHC-UC-22)."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.phc.models import DoctorAttendance, DoctorSchedule, ScheduleSlot


def _validate_slots(slots: list[dict]) -> None:
    if not slots:
        raise BadRequestError("Add at least one day and time to the schedule.",
                              code="schedule_without_slots")
    seen = set()
    for slot in slots:
        if slot["end_time"] <= slot["start_time"]:
            raise BadRequestError("Each slot must end after it starts.",
                                  code="slot_ends_before_start")
        key = (slot["day_of_week"], slot["start_time"])
        if key in seen:
            raise BadRequestError("Two slots start at the same time on the same day.",
                                  code="duplicate_slot")
        seen.add(key)


def _locked(schedule_id: int) -> DoctorSchedule:
    schedule = DoctorSchedule.objects.select_for_update().filter(pk=schedule_id).first()
    if schedule is None:
        raise NotFoundError("That doctor schedule does not exist.")
    return schedule


@transaction.atomic
def create_schedule(*, actor, doctor_name: str, specialization: str,
                    slots: list[dict]) -> DoctorSchedule:
    # PHC-UC-22 M1
    _validate_slots(slots)
    schedule = DoctorSchedule.objects.create(doctor_name=doctor_name,
                                             specialization=specialization,
                                             created_by_user_id=actor.user_id)
    ScheduleSlot.objects.bulk_create(ScheduleSlot(schedule=schedule, **s) for s in slots)
    return schedule


@transaction.atomic
def update_schedule(*, actor, schedule_id: int, doctor_name: str, specialization: str,
                    slots: list[dict]) -> DoctorSchedule:
    # PHC-UC-07: the whole week is replaced at once, or nothing changes.
    _validate_slots(slots)
    schedule = _locked(schedule_id)
    schedule.doctor_name = doctor_name
    schedule.specialization = specialization
    schedule.save(update_fields=("doctor_name", "specialization", "updated_at"))
    schedule.slots.all().delete()
    ScheduleSlot.objects.bulk_create(ScheduleSlot(schedule=schedule, **s) for s in slots)
    return schedule


@transaction.atomic
def publish_schedule(*, actor, schedule_id: int) -> DoctorSchedule:
    # PHC-UC-22 M3
    schedule = _locked(schedule_id)
    if schedule.is_published:
        raise ConflictError("This schedule is already published.", code="already_published")
    if not schedule.slots.exists():
        raise ConflictError("Add at least one day and time before publishing.",
                            code="schedule_without_slots")
    schedule.is_published = True
    schedule.published_at = timezone.now()
    schedule.save(update_fields=("is_published", "published_at", "updated_at"))
    return schedule


@transaction.atomic
def mark_attendance(*, actor, schedule_id: int, status: str) -> DoctorAttendance:
    # PHC-UC-08: one row per doctor per day, holding the latest arrival or departure.
    schedule = _locked(schedule_id)
    row, _ = DoctorAttendance.objects.update_or_create(
        schedule=schedule, attendance_date=timezone.localdate(),
        defaults={"status": status, "updated_by_user_id": actor.user_id})
    return row
