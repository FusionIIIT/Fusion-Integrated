"""Doctor, Schedule and Attendance services (CFR-PHC-001, UC-PHC-07, 08, 22)."""
from datetime import date, time
from typing import Sequence
from django.utils import timezone

from modules.phc.models.doctors import Doctor, DoctorAttendance, DoctorSchedule


def create_doctor(
    name: str,
    specialization: str,
    contact_phone: str = "",
    email: str = "",
    is_visiting: bool = True,
) -> Doctor:
    return Doctor.objects.create(
        name=name.strip(),
        specialization=specialization.strip(),
        contact_phone=contact_phone.strip(),
        email=email.strip(),
        is_visiting=is_visiting,
        is_active=True,
    )


def create_or_update_schedule(
    doctor_id: int,
    day_of_week: str,
    start_time: time,
    end_time: time,
    room_number: str = "",
    is_published: bool = False,
    schedule_id: int | None = None,
) -> DoctorSchedule:
    doctor = Doctor.objects.get(id=doctor_id)
    if schedule_id:
        schedule = DoctorSchedule.objects.get(id=schedule_id, doctor=doctor)
        schedule.day_of_week = day_of_week
        schedule.start_time = start_time
        schedule.end_time = end_time
        schedule.room_number = room_number
        schedule.is_published = is_published
        schedule.save()
        return schedule

    return DoctorSchedule.objects.create(
        doctor=doctor,
        day_of_week=day_of_week,
        start_time=start_time,
        end_time=end_time,
        room_number=room_number,
        is_published=is_published,
    )


def publish_schedules(schedule_ids: Sequence[int]) -> int:
    """Publishes schedules for patient visibility (AFR-PHC-005, UC-PHC-22)."""
    return DoctorSchedule.objects.filter(id__in=schedule_ids).update(is_published=True)


def mark_attendance(
    doctor_id: int,
    status: str,
    marked_by_user_id: int,
    attendance_date: date | None = None,
    remarks: str = "",
) -> DoctorAttendance:
    """Marks real-time attendance for visiting doctors (AFR-PHC-003, UC-PHC-08)."""
    doctor = Doctor.objects.get(id=doctor_id)
    att_date = attendance_date or timezone.now().date()
    attendance, _ = DoctorAttendance.objects.update_or_create(
        doctor=doctor,
        date=att_date,
        defaults={
            "status": status,
            "marked_by_user_id": marked_by_user_id,
            "remarks": remarks,
        },
    )
    return attendance
