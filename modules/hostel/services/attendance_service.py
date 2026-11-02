"""Student attendance recording and monitoring services (3.3, CFR-HM-008, BR-HM-011)."""

from datetime import date
from typing import Any
from django.db import transaction
from ..domain.constants import AttendanceStatus
from ..domain.errors import HostelDomainError, InactiveHostelError
from ..models import AttendanceRecord, Hostel


@transaction.atomic
def record_attendance_batch(
    caretaker_user_id: int,
    hostel_id: int,
    date_val: date,
    records: list[dict[str, Any]],
) -> list[AttendanceRecord]:
    """Caretaker records or updates attendance for students in assigned hostel (HM-UC-012, BR-HM-011)."""
    hostel = Hostel.objects.filter(id=hostel_id).first()
    if not hostel:
        raise HostelDomainError(f"Hostel {hostel_id} not found.", code="not_found")
    if not hostel.is_active:
        raise InactiveHostelError(hostel.name)

    saved_records = []
    valid_statuses = {s.value for s in AttendanceStatus}

    for item in records:
        student_user_id = item["student_user_id"]
        roll_number = item["student_roll_number"]
        name = item.get("student_name", "")
        status = item.get("status", AttendanceStatus.PRESENT.value)
        remarks = item.get("remarks", "")

        if status not in valid_statuses:
            status = AttendanceStatus.PRESENT.value

        rec, _ = AttendanceRecord.objects.update_or_create(
            hostel=hostel,
            student_user_id=student_user_id,
            date=date_val,
            defaults={
                "student_roll_number": roll_number,
                "student_name": name,
                "status": status,
                "marked_by_user_id": caretaker_user_id,
                "remarks": remarks,
            },
        )
        saved_records.append(rec)

    return saved_records
