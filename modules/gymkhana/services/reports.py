"""Event report services (UC-GYM-010, BR-GYM-019)."""
from __future__ import annotations

import datetime

from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError
from core.files import drive
from core.files.drive import InvalidDriveLink
from modules.directory import contracts as directory
from modules.gymkhana.models import Club, ClubEventReport


def submit_event_report(
    *,
    club: Club,
    student_incharge_id: int,
    event_name: str,
    event_date: datetime.date,
    event_time: datetime.time,
    description: str,
    report_file_url: str,
    user_id: int,
) -> ClubEventReport:
    """Submit a documented report for a completed club event (UC-GYM-010)."""
    if user_id not in (club.coordinator_id, club.co_coordinator_id):
        raise ConflictError(
            "Only the current club coordinator or co-coordinator may submit event reports.",
            code="not_club_head",
        )

    users = directory.get_users([student_incharge_id])
    incharge = users.get(student_incharge_id)
    if not incharge or incharge.kind != "student":
        raise BadRequestError(
            f"User {student_incharge_id} is not a valid student.",
            code="invalid_student_incharge",
        )

    try:
        drive_ref = drive.parse(report_file_url)
    except InvalidDriveLink as exc:
        raise BadRequestError(exc.message, code=exc.code) from exc

    with transaction.atomic():
        return ClubEventReport.objects.create(
            club=club,
            student_incharge_id=student_incharge_id,
            event_name=event_name,
            event_date=event_date,
            event_time=event_time,
            description=description,
            report_file_url=drive_ref.url,
            report_file_id=drive_ref.file_id,
            submitted_by_user_id=user_id,
        )
