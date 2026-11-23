"""Club event report services for Gymkhana."""

from __future__ import annotations

import datetime

from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.directory.contracts import get_users
from modules.gymkhana.domain.constants import CLUB_STATUS_CONFIRMED, DOCUMENT_EXTENSIONS
from modules.gymkhana.domain.exceptions import DomainError
from modules.gymkhana.domain.validation import (
    validate_event_has_occurred,
    validate_file_present,
)
from modules.gymkhana.models.club import Club
from modules.gymkhana.models.report import ClubEventReport
from modules.gymkhana.selectors.scoping import is_club_head
from modules.gymkhana.services.uploads import check_upload


@transaction.atomic
def submit_event_report(
    *,
    club_id: int,
    actor_id: int,
    student_incharge_id: int,
    event_name: str,
    event_date: datetime.datetime,
    description: str,
    report_file,
) -> ClubEventReport:
    """Store a club's report on a past event (UC-GYM-010, AFR-GYM-032)."""
    club = Club.objects.filter(id=club_id).first()
    if not club:
        raise NotFoundError(f"Club {club_id} not found.")

    if not is_club_head(actor_id, club):
        raise PermissionDeniedError("Only the active Club Head can submit event reports.")

    if club.status != CLUB_STATUS_CONFIRMED:
        raise ConflictError("Event reports can only be submitted for confirmed clubs.")

    users = get_users([student_incharge_id])
    incharge = users.get(student_incharge_id)
    if not incharge or incharge.kind != "student":
        raise BadRequestError(f"Student incharge {student_incharge_id} must be a valid student.")

    try:
        validate_file_present(bool(report_file), "report_file")
        validate_event_has_occurred(event_date, datetime.datetime.now(datetime.UTC))
    except DomainError as exc:
        raise BadRequestError(str(exc)) from exc
    check_upload(report_file, DOCUMENT_EXTENSIONS)

    return ClubEventReport.objects.create(
        club=club,
        submitted_by_id=actor_id,
        student_incharge_id=student_incharge_id,
        event_name=event_name.strip(),
        event_date=event_date,
        description=description.strip(),
        report_file=report_file,
    )
