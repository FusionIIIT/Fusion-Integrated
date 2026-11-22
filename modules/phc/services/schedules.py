"""Schedule and attendance writes (AFR-PHC-001..005)."""
from __future__ import annotations

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.phc.domain.policy import SCHEDULE_DUPLICATE_MESSAGE
from modules.phc.models import DoctorAttendance, DoctorSchedule
from modules.phc.services import audit

NOT_FOUND = "No such schedule. Refresh the list and choose one that is still available."


def _day_is_taken(doctor_name: str, day_of_week: int, exclude_pk=None) -> bool:
    qs = DoctorSchedule.objects.filter(doctor_name=doctor_name,
                                       day_of_week=day_of_week)
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    return qs.exists()


@transaction.atomic
def create(actor, validated: dict) -> DoctorSchedule:
    name, day = validated["doctor_name"], validated["day_of_week"]
    if _day_is_taken(name, day):
        raise ConflictError(SCHEDULE_DUPLICATE_MESSAGE, code="schedule_exists")
    try:
        # A savepoint keeps the outer transaction usable if a concurrent insert
        # wins the unique-constraint race between the check and the write.
        with transaction.atomic():
            schedule = DoctorSchedule.objects.create(
                doctor_name=name,
                day_of_week=day,
                start_time=validated["start_time"],
                end_time=validated["end_time"],
                is_published=False,
                published_by=getattr(actor, "user_id", None),
            )
    except IntegrityError as exc:
        raise ConflictError(SCHEDULE_DUPLICATE_MESSAGE,
                            code="schedule_exists") from exc
    audit.record(actor, "schedule.create", "schedule", schedule.pk, validated)
    return schedule


@transaction.atomic
def maintain(actor, pk: int, validated: dict) -> DoctorSchedule:
    schedule = DoctorSchedule.objects.filter(pk=pk).first()
    if schedule is None:
        raise NotFoundError(NOT_FOUND, code="not_found")
    day = validated.get("day_of_week", schedule.day_of_week)
    if _day_is_taken(schedule.doctor_name, day, exclude_pk=pk):
        raise ConflictError(SCHEDULE_DUPLICATE_MESSAGE, code="schedule_exists")
    for field in ("day_of_week", "start_time", "end_time"):
        if field in validated:
            setattr(schedule, field, validated[field])
    try:
        with transaction.atomic():
            schedule.save()
    except IntegrityError as exc:
        raise ConflictError(SCHEDULE_DUPLICATE_MESSAGE,
                            code="schedule_exists") from exc
    audit.record(actor, "schedule.maintain", "schedule", pk, validated)
    return schedule


@transaction.atomic
def publish(actor, pk: int) -> DoctorSchedule:
    schedule = DoctorSchedule.objects.filter(pk=pk).first()
    if schedule is None:
        raise NotFoundError(NOT_FOUND, code="not_found")
    schedule.is_published = True
    schedule.published_at = timezone.now()
    schedule.published_by = getattr(actor, "user_id", None)
    schedule.save()
    audit.record(actor, "schedule.publish", "schedule", pk, {})
    return schedule


@transaction.atomic
def mark_attendance(actor, validated: dict) -> DoctorAttendance:
    attendance, _ = DoctorAttendance.objects.update_or_create(
        doctor_name=validated["doctor_name"], date=validated["date"],
        defaults={"status": validated["status"],
                  "updated_by": getattr(actor, "user_id", None)},
    )
    audit.record(actor, "attendance.mark", "attendance", attendance.pk, validated)
    return attendance
