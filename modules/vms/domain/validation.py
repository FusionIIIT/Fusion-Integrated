"""Pure python validation rules for visiting hours, durations, and mandatory fields.

ZERO framework imports allowed here.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta

VALID_DOCUMENT_TYPES = {
    "AADHAAR",
    "PAN",
    "PASSPORT",
    "VOTER_ID",
    "DRIVING_LICENSE",
    "INSTITUTE_ID",
    "OTHER",
}


class ValidationError(ValueError):
    """Domain validation error."""


def validate_mandatory_visitor_fields(
    name: str | None,
    email: str | None,
    phone: str | None,
    host_id: int | None,
    purpose: str | None,
    id_document_type: str | None,
    id_document_number: str | None,
) -> None:
    """Ensure all mandatory pre-registration fields are present and valid."""
    missing = []
    if not name or not name.strip():
        missing.append("name")
    if not email or not email.strip() or "@" not in email:
        missing.append("email")
    if not phone or not phone.strip():
        missing.append("phone")
    if not host_id or host_id <= 0:
        missing.append("host_id")
    if not purpose or not purpose.strip():
        missing.append("purpose")
    if not id_document_type or id_document_type not in VALID_DOCUMENT_TYPES:
        missing.append("id_document_type")
    if not id_document_number or not id_document_number.strip():
        missing.append("id_document_number")

    if missing:
        raise ValidationError(f"Missing or invalid mandatory fields: {', '.join(missing)}")


def validate_advance_window(
    scheduled_start: datetime,
    submission_time: datetime,
    is_urgent_exception: bool = False,
    min_advance_hours: int = 2,
) -> None:
    """Validate advance pre-registration window (BR-202).

    Must be submitted at least `min_advance_hours` before scheduled start,
    unless flagged as urgent exception by Admin (BR-203).
    """
    if is_urgent_exception:
        return

    earliest_allowed = submission_time + timedelta(hours=min_advance_hours)
    if scheduled_start < earliest_allowed:
        raise ValidationError(
            f"Pre-registration must be submitted at least {min_advance_hours} hours in advance."
        )


def validate_visit_duration(
    scheduled_start: datetime,
    scheduled_end: datetime,
    max_duration_hours: int = 12,
) -> None:
    """Validate scheduled start is before end and within maximum duration (BR-193)."""
    if scheduled_end <= scheduled_start:
        raise ValidationError("Scheduled end time must be after scheduled start time.")

    duration = scheduled_end - scheduled_start
    if duration > timedelta(hours=max_duration_hours):
        hours = duration.total_seconds() / 3600
        raise ValidationError(
            f"Visit duration ({hours:.1f}h) exceeds maximum allowed "
            f"duration of {max_duration_hours}h."
        )


def validate_visiting_hours(
    scheduled_time: datetime,
    hours_start: time = time(8, 0),
    hours_end: time = time(20, 0),
) -> None:
    """Validate scheduled time falls within campus visiting hours."""
    t = scheduled_time.time()
    if t < hours_start or t > hours_end:
        s_str = hours_start.strftime("%H:%M")
        e_str = hours_end.strftime("%H:%M")
        raise ValidationError(
            f"Scheduled time ({t.strftime('%H:%M')}) is outside campus "
            f"visiting hours ({s_str} - {e_str})."
        )
