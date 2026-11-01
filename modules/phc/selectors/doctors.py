"""Doctor schedule and availability selectors (CFR-PHC-001, PHC-BR-01)."""
from datetime import date
from typing import Any
from django.utils import timezone

from modules.phc.models.doctors import Doctor, DoctorAttendance, DoctorSchedule


def get_patient_doctor_availability(query_date: date | None = None) -> list[dict[str, Any]]:
    """Combines published master weekly schedule with current-day real-time attendance (PHC-BR-01)."""
    target_date = query_date or timezone.now().date()
    day_name = target_date.strftime("%A")

    # Fetch active doctors with published schedules
    doctors = Doctor.objects.filter(is_active=True).prefetch_related("schedules", "attendance_records")

    result = []
    for doc in doctors:
        # Published weekly schedules for this doctor
        schedules = [
            {
                "id": s.id,
                "day_of_week": s.day_of_week,
                "start_time": s.start_time.strftime("%H:%M"),
                "end_time": s.end_time.strftime("%H:%M"),
                "room_number": s.room_number,
            }
            for s in doc.schedules.filter(is_published=True)
        ]

        # Real-time attendance for target_date
        attendance = doc.attendance_records.filter(date=target_date).first()
        live_status = attendance.status if attendance else ("Available" if any(s["day_of_week"] == day_name for s in schedules) else "Not Scheduled")
        remarks = attendance.remarks if attendance else ""

        result.append({
            "doctor_id": doc.id,
            "doctor_name": doc.name,
            "specialization": doc.specialization,
            "contact_phone": doc.contact_phone,
            "is_visiting": doc.is_visiting,
            "weekly_schedule": schedules,
            "today_attendance": {
                "date": str(target_date),
                "day": day_name,
                "status": live_status,
                "remarks": remarks,
            },
        })

    return result


def get_all_doctors() -> list[Doctor]:
    return list(Doctor.objects.filter(is_active=True))


def get_all_schedules() -> list[DoctorSchedule]:
    return list(DoctorSchedule.objects.select_related("doctor").all())


def get_today_attendance(target_date: date | None = None) -> list[DoctorAttendance]:
    att_date = target_date or timezone.now().date()
    return list(DoctorAttendance.objects.filter(date=att_date).select_related("doctor"))
