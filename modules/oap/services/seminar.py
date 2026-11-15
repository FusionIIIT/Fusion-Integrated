from datetime import date
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.oap.domain import constants as c
from modules.oap.domain.state_machine import (
    InvalidStateTransitionError,
    SeminarStateMachine,
)
from modules.oap.domain.validation import (
    DomainValidationError,
    validate_seminar_request,
    validate_seminar_scheduling,
)
from modules.oap.models.seminar import GraduateSeminar
from modules.oap.selectors.seminar import get_seminar_by_id
from modules.oap.services.notify import emit_notification


def request_graduate_seminar(
    user_id: int,
    title: str,
    abstract: str,
    preferred_dates: str = "",
) -> GraduateSeminar:
    """PG student requests graduate seminar scheduling (OA-UC-51, OA-BR-61)."""
    try:
        validate_seminar_request(title, abstract)
    except DomainValidationError as exc:
        raise BadRequestError(str(exc)) from exc

    seminar = GraduateSeminar.objects.create(
        user_id=user_id,
        title=title,
        abstract=abstract,
        preferred_dates=preferred_dates,
        status=SeminarStateMachine.initial_state(),
    )

    emit_notification(
        recipient_user_id=user_id,
        title="Graduate Seminar Requested",
        message=f"Your graduate seminar scheduling request '{title}' has been submitted.",
        related_entity_type="seminar",
        related_entity_id=seminar.id,
    )

    return seminar


def schedule_graduate_seminar(
    seminar_id: int,
    dept_admin_user_id: int,
    scheduled_date: date,
    scheduled_time: str,
    venue: str,
    coordinator_user_id: int | None = None,
    remarks: str = "",
) -> GraduateSeminar:
    """Department Administrator schedules a graduate seminar (OA-UC-53, OA-BR-62)."""
    seminar = get_seminar_by_id(seminar_id)
    if not seminar:
        raise NotFoundError(f"Graduate seminar {seminar_id} not found.")

    try:
        validate_seminar_scheduling(scheduled_date, scheduled_time, venue)
    except DomainValidationError as exc:
        raise BadRequestError(str(exc)) from exc

    try:
        new_status = SeminarStateMachine.schedule(seminar.status)
    except InvalidStateTransitionError as exc:
        raise ConflictError(str(exc)) from exc

    seminar.status = new_status
    seminar.scheduled_date = scheduled_date
    seminar.scheduled_time = scheduled_time
    seminar.venue = venue
    seminar.coordinator_user_id = coordinator_user_id
    seminar.scheduled_by_user_id = dept_admin_user_id
    seminar.scheduled_at = timezone.now()
    seminar.remarks = remarks
    seminar.save(update_fields=[
        "status",
        "scheduled_date",
        "scheduled_time",
        "venue",
        "coordinator_user_id",
        "scheduled_by_user_id",
        "scheduled_at",
        "remarks",
        "updated_at",
    ])

    emit_notification(
        recipient_user_id=seminar.user_id,
        title="Graduate Seminar Scheduled",
        message=f"Your seminar '{seminar.title}' has been scheduled on {scheduled_date} at {scheduled_time} in {venue}.",
        related_entity_type="seminar",
        related_entity_id=seminar.id,
    )

    return seminar
