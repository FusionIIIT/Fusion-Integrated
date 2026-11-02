"""Student attendance management services (CFR-HM-009, 010, HM-UC-012, 013, 036, BR-HM-011)."""

from __future__ import annotations

from datetime import date

from django.db import transaction

from modules.hostel.domain.constants import AttendanceStatus
from modules.hostel.models import AttendanceRecord, Hostel


@transaction.atomic
def record_daily_attendance(
    hostel_id: int,
    attendance_date: date,
    student_attendance_list: list[dict],
    recorded_by_user_id: int | None = None,
) -> list[AttendanceRecord]:
    """CFR-HM-009, HM-UC-012: Caretaker records attendance for a batch of students."""
    hostel = Hostel.objects.get(id=hostel_id)
    created_records = []

    for item in student_attendance_list:
        student_id = item.get("student_user_id")
        status = item.get("status", AttendanceStatus.PRESENT.value)
        remarks = item.get("remarks", "")

        if not student_id:
            continue

        record, _ = AttendanceRecord.objects.update_or_create(
            student_user_id=student_id,
            date=attendance_date,
            defaults={
                "hostel": hostel,
                "status": status,
                "recorded_by_user_id": recorded_by_user_id,
                "remarks": remarks.strip(),
            },
        )
        created_records.append(record)

    return created_records
