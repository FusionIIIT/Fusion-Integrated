from django.db import IntegrityError, transaction

from core.api.exceptions import ConflictError, NotFoundError
from modules.phc.models import Doctor, DoctorScheduleSlot
from modules.phc.services.common import audit


def create_doctor(*, display_name: str, specialization: str) -> Doctor:
    return Doctor.objects.create(display_name=display_name,
                                 specialization=specialization)


def create_doctor_slot(*, doctor_id: int | None, display_name: str,
                       specialization: str, day_of_week: int, starts_at, ends_at,
                       actor_user_id: int) -> DoctorScheduleSlot:
    try:
        with transaction.atomic():
            if doctor_id is None:
                doctor = Doctor.objects.create(
                    display_name=display_name, specialization=specialization)
            else:
                doctor = Doctor.objects.select_for_update().get(
                    pk=doctor_id, is_active=True)
            slot = DoctorScheduleSlot.objects.create(
                doctor=doctor, day_of_week=day_of_week,
                starts_at=starts_at, ends_at=ends_at)
            audit(actor_user_id=actor_user_id, action="schedule.created",
                  object_type="doctor_schedule_slot", object_id=slot.pk)
            return slot
    except Doctor.DoesNotExist as exc:
        raise NotFoundError("Select an active doctor before adding a schedule.",
                            code="doctor_not_found") from exc
    except IntegrityError as exc:
        raise ConflictError("That doctor already has an overlapping slot on this day.",
                            code="schedule_overlap") from exc


def create_slot(*, doctor_id: int, day_of_week: int, starts_at, ends_at,
                actor_user_id: int) -> DoctorScheduleSlot:
    try:
        with transaction.atomic():
            doctor = Doctor.objects.select_for_update().get(pk=doctor_id,
                                                            is_active=True)
            slot = DoctorScheduleSlot.objects.create(
                doctor=doctor,
                day_of_week=day_of_week,
                starts_at=starts_at,
                ends_at=ends_at,
            )
            audit(actor_user_id=actor_user_id, action="schedule.created",
                  object_type="doctor_schedule_slot", object_id=slot.pk)
            return slot
    except Doctor.DoesNotExist as exc:
        raise NotFoundError("Select an active doctor before adding a schedule.",
                            code="doctor_not_found") from exc
    except IntegrityError as exc:
        raise ConflictError("That doctor already has an overlapping slot on this day.",
                            code="schedule_overlap") from exc


def update_slot(*, slot_id: int, changes: dict, actor_user_id: int) -> DoctorScheduleSlot:
    try:
        with transaction.atomic():
            slot = DoctorScheduleSlot.objects.select_for_update().get(pk=slot_id)
            for name, value in changes.items():
                setattr(slot, name, value)
            slot.save()
            audit(actor_user_id=actor_user_id, action="schedule.updated",
                  object_type="doctor_schedule_slot", object_id=slot.pk)
            return slot
    except DoctorScheduleSlot.DoesNotExist as exc:
        raise NotFoundError("That schedule slot no longer exists.",
                            code="schedule_not_found") from exc
    except IntegrityError as exc:
        raise ConflictError("That doctor already has an overlapping slot on this day.",
                            code="schedule_overlap") from exc


def publish_slot(*, slot_id: int, actor_user_id: int) -> DoctorScheduleSlot:
    try:
        with transaction.atomic():
            slot = DoctorScheduleSlot.objects.select_for_update().get(
                pk=slot_id, doctor__is_active=True)
            slot.publication = DoctorScheduleSlot.Publication.PUBLISHED
            slot.save(update_fields=["publication", "updated_at"])
            audit(actor_user_id=actor_user_id, action="schedule.published",
                  object_type="doctor_schedule_slot", object_id=slot.pk)
            return slot
    except DoctorScheduleSlot.DoesNotExist as exc:
        raise NotFoundError("That active doctor schedule no longer exists.",
                            code="schedule_not_found") from exc


def set_attendance(*, doctor_id: int, attendance_date, status: str,
                   actor_user_id: int):
    from modules.phc.models import DoctorAttendance

    try:
        with transaction.atomic():
            Doctor.objects.select_for_update().get(pk=doctor_id, is_active=True)
            attendance, _ = DoctorAttendance.objects.get_or_create(
                doctor_id=doctor_id,
                attendance_date=attendance_date,
                defaults={"status": status, "updated_by_user_id": actor_user_id},
            )
            attendance = DoctorAttendance.objects.select_for_update().get(pk=attendance.pk)
            if attendance.updated_by_user_id != actor_user_id or attendance.status != status:
                attendance.status = status
                attendance.updated_by_user_id = actor_user_id
                attendance.save(update_fields=["status", "updated_by_user_id", "updated_at"])
            audit(actor_user_id=actor_user_id, action="attendance.changed",
                  object_type="doctor_attendance", object_id=attendance.pk,
                  metadata={"status": attendance.status})
            return attendance
    except Doctor.DoesNotExist as exc:
        raise NotFoundError("Select an active doctor before marking attendance.",
                            code="doctor_not_found") from exc
