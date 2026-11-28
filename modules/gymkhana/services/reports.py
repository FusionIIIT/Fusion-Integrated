"""Club event reports (UC-GYM-010); review is a read (UC-GYM-012)."""
from __future__ import annotations

from datetime import datetime

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import NotFoundError
from modules.gymkhana.domain import rules
from modules.gymkhana.domain.rules import RuleViolation
from modules.gymkhana.models import EventReport
from modules.gymkhana.selectors import scoping
from modules.gymkhana.services import audit, links, people
from modules.gymkhana.services.authz import require
from modules.gymkhana.services.errors import refused
from modules.gymkhana.services.inputs import NOT_LED, required_text

P_SUBMIT = "gymkhana.event_report.create"


@transaction.atomic
def submit(*, actor, club_id: int, student_incharge_user_id: int, event_name: str,
           event_at: datetime, description: str, report_url: str) -> EventReport:
    require(actor, P_SUBMIT)
    club = scoping.led_clubs(actor).filter(pk=club_id).first()
    if club is None:
        raise NotFoundError(NOT_LED)
    event_name = required_text(event_name, "event_name", "Enter the event's name.")
    description = required_text(description, "description", "Describe the event.")
    report = links.parse_link(
        report_url, field="report_url", missing_code="report_file_required",
        missing_message="An event report needs its report file. Paste the Google "
                        "Drive link to it.")
    try:
        rules.check_event_held(event_at, timezone.now())
        rules.check_event_after_club(timezone.localdate(event_at),
                                     timezone.localdate(club.created_at))
    except RuleViolation as exc:
        raise refused(exc) from exc
    people.require_students({"student_incharge_user_id": student_incharge_user_id})
    row = EventReport.objects.create(
        club=club, student_incharge_user_id=student_incharge_user_id,
        event_name=event_name, event_at=event_at, description=description,
        report_link=report.url, report_file_id=report.file_id,
        submitted_by_user_id=actor.user_id)
    audit.record("event_report.submitted", object_type="event_report",
                 object_id=row.pk, actor=actor, club_id=club.pk)
    return row
