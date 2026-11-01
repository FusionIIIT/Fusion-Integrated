"""Service layer for Graduate Seminar Scheduling workflows (BW-OAP-09)."""
from __future__ import annotations

import datetime
from django.db import transaction
from core.api.exceptions import BadRequestError, NotFoundError, PermissionDeniedError

from modules.department.domain import eligibility
from modules.department.domain.state_machine import (
    SeminarStatus,
    SeminarEvent,
    can_transition,
)
from modules.department.models.seminar import (
    SeminarSchedulingRequest,
    GraduateSeminar,
    SeminarSchedulingHistory,
)


def _get_user_id(actor) -> int:
    if hasattr(actor, "user_id"):
        return actor.user_id
    if hasattr(actor, "id"):
        return actor.id
    return 0


def _get_user_name(actor) -> str:
    if hasattr(actor, "display_name") and actor.display_name:
        return actor.display_name
    if hasattr(actor, "username") and actor.username:
        return actor.username
    return "User"


@transaction.atomic
def submit_seminar_request(
    actor,
    topic: str,
    abstract: str,
    programme: str = "M.Tech",
    department: str = "",
    preferred_date: datetime.date | None = None,
    faculty_advisor_id: int | None = None,
    faculty_advisor_name: str = "",
) -> SeminarSchedulingRequest:
    """Submit a graduate seminar scheduling request (OA-UC-51, OA-BR-61)."""
    # 1. Eligibility Check (OA-BR-61)
    elig = eligibility.check_seminar_eligibility(programme)
    if not elig.allowed:
        raise BadRequestError(elig.reason, code="ineligible_pg_scope")

    # 2. Input validation
    valid, msg = eligibility.validate_seminar_request(topic, abstract, preferred_date)
    if not valid:
        raise BadRequestError(msg, code="invalid_request_parameters")

    # 3. Prevent duplicate active pending requests
    user_id = _get_user_id(actor)
    existing_pending = SeminarSchedulingRequest.objects.filter(
        student_id=user_id,
        status=SeminarStatus.AWAITING_SCHEDULING.value,
    ).first()
    if existing_pending:
        raise BadRequestError(
            f"You already have a pending seminar request (#{existing_pending.pk}). "
            "Please wait until it is scheduled or cancelled.",
            code="duplicate_pending_request",
        )

    # 4. Create request in AWAITING_SCHEDULING status
    req = SeminarSchedulingRequest.objects.create(
        student_id=user_id,
        student_name=_get_user_name(actor),
        programme=programme,
        department=department,
        topic=topic.strip(),
        abstract=abstract.strip(),
        preferred_date=preferred_date,
        faculty_advisor_id=faculty_advisor_id,
        faculty_advisor_name=faculty_advisor_name.strip(),
        status=SeminarStatus.AWAITING_SCHEDULING.value,
    )
    return req


@transaction.atomic
def schedule_graduate_seminar(
    actor,
    request_id: int,
    scheduled_date: datetime.date,
    start_time: datetime.time,
    end_time: datetime.time,
    venue: str,
    session_chair: str = "",
    remarks: str = "",
) -> GraduateSeminar:
    """Department Administrator schedules a seminar for a pending request (OA-UC-53, OA-BR-62)."""
    req = SeminarSchedulingRequest.objects.filter(pk=request_id).first()
    if not req:
        raise NotFoundError(f"Seminar request #{request_id} not found.", code="not_found")

    # 1. Guard check: Status must be Awaiting Scheduling (OA-BR-62)
    allowed, msg, _ = can_transition(req.status, SeminarEvent.SCHEDULE.value)
    if not allowed:
        raise BadRequestError(
            f"Cannot schedule seminar: request #{request_id} is in status '{req.status}' "
            "(only AWAITING_SCHEDULING requests may be scheduled).",
            code="invalid_state_transition",
        )

    # 2. Validate scheduling parameters
    valid, param_msg = eligibility.validate_scheduling_parameters(
        scheduled_date=scheduled_date,
        start_time=start_time,
        end_time=end_time,
        venue=venue,
    )
    if not valid:
        raise BadRequestError(param_msg, code="invalid_scheduling_parameters")

    # 3. Transition request status to SCHEDULED
    req.status = SeminarStatus.SCHEDULED.value
    req.save(update_fields=["status", "updated_at"])

    # 4. Create GraduateSeminar record
    admin_id = _get_user_id(actor)
    admin_name = _get_user_name(actor)
    seminar = GraduateSeminar.objects.create(
        request=req,
        title=req.topic,
        speaker_id=req.student_id,
        speaker_name=req.student_name,
        scheduled_date=scheduled_date,
        start_time=start_time,
        end_time=end_time,
        venue=venue.strip(),
        session_chair=session_chair.strip(),
        remarks=remarks.strip(),
        scheduled_by_id=admin_id,
        scheduled_by_name=admin_name,
    )

    # 5. Log audit entry in SeminarSchedulingHistory (AFR-OAP-048)
    history_details = (
        f"Seminar scheduled on {scheduled_date} from {start_time} to {end_time} "
        f"at venue '{venue}'. Session Chair: '{session_chair}'."
    )
    SeminarSchedulingHistory.objects.create(
        seminar=seminar,
        action="SCHEDULED",
        details=history_details,
        recorded_by_id=admin_id,
        recorded_by_name=admin_name,
    )

    return seminar


@transaction.atomic
def reject_seminar_request(
    actor,
    request_id: int,
    reason: str,
) -> SeminarSchedulingRequest:
    """Department Administrator rejects a seminar request."""
    req = SeminarSchedulingRequest.objects.filter(pk=request_id).first()
    if not req:
        raise NotFoundError(f"Seminar request #{request_id} not found.", code="not_found")

    allowed, msg, _ = can_transition(req.status, SeminarEvent.REJECT.value)
    if not allowed:
        raise BadRequestError(msg, code="invalid_state_transition")

    req.status = SeminarStatus.REJECTED.value
    req.rejection_reason = reason.strip()
    req.save(update_fields=["status", "rejection_reason", "updated_at"])
    return req


@transaction.atomic
def cancel_seminar_request(
    actor,
    request_id: int,
) -> SeminarSchedulingRequest:
    """Student withdraws/cancels their pending seminar request."""
    req = SeminarSchedulingRequest.objects.filter(pk=request_id).first()
    if not req:
        raise NotFoundError(f"Seminar request #{request_id} not found.", code="not_found")

    user_id = _get_user_id(actor)
    if req.student_id != user_id and not (hasattr(actor, "has_permission") and actor.has_permission("department.seminar.schedule")):
        raise PermissionDeniedError("You may only cancel your own seminar requests.", code="permission_denied")

    allowed, msg, _ = can_transition(req.status, SeminarEvent.CANCEL.value)
    if not allowed:
        raise BadRequestError(msg, code="invalid_state_transition")

    req.status = SeminarStatus.CANCELLED.value
    req.save(update_fields=["status", "updated_at"])
    return req
