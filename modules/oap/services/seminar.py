from django.db import transaction

from modules.oap.domain import seminar as rules
from modules.oap.domain.eligibility import is_pg
from modules.oap.domain.errors import InvalidTransition
from modules.oap.models import SeminarRequest
from modules.oap.services.common import (
    ServiceError,
    department_of,
    directory_user,
    notify,
    record_event,
)

CASE_TYPE = "seminar"


def submit_seminar(student_id):
    """BW-OAP-09 row 1 (OA-UC-51). PG students only (OA-BR-61)."""
    user = directory_user(student_id)
    if not is_pg(getattr(user, "programme", None)):
        raise ServiceError("Only PG students can request a seminar.")

    with transaction.atomic():
        try:
            status = rules.transition(rules.START_STATE, "submit")
        except InvalidTransition as e:
            raise ServiceError(str(e)) from e
        obj = SeminarRequest.objects.create(
            student_id=student_id,
            department=department_of(student_id),
            status=status,
        )
        record_event(CASE_TYPE, obj, rules.START_STATE, status, "submit", student_id)
        notify(student_id, "Seminar request submitted", CASE_TYPE, obj.id)
    return obj


def schedule_seminar(request_id, actor_id, scheduled_at, venue=""):
    """BW-OAP-09 row 2 (OA-UC-53)."""
    if not scheduled_at:
        raise ServiceError("A scheduled date and time is required.")

    with transaction.atomic():
        obj = SeminarRequest.objects.select_for_update().get(pk=request_id)
        actor_department = department_of(actor_id)
        if not actor_department or actor_department != obj.department:
            raise SeminarRequest.DoesNotExist

        from_state = obj.status
        try:
            obj.status = rules.transition(from_state, "schedule")
        except InvalidTransition as e:
            raise ServiceError(str(e)) from e
        obj.scheduled_at = scheduled_at
        obj.venue = venue
        obj.scheduled_by_id = actor_id
        obj.save()

        # The event row keeps the scheduling history (AFR-OAP-048).
        record_event(
            CASE_TYPE, obj, from_state, obj.status, "schedule", actor_id, venue
        )
        notify(obj.student_id, "Your seminar has been scheduled", CASE_TYPE, obj.id)
    return obj


def scheduled_seminars():
    """OA-UC-54."""
    return SeminarRequest.objects.filter(status=rules.SCHEDULED).order_by(
        "scheduled_at"
    )
