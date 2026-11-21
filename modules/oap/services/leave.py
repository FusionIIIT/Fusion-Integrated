from django.db import transaction
from django.utils import timezone

from modules.oap.domain import leave as rules
from modules.oap.domain.errors import InvalidTransition
from modules.oap.models import LeaveApplication
from modules.oap.services.common import (
    ServiceError,
    department_of,
    notify,
    record_event,
)

CASE_TYPE = "leave"

_DECISION_WORDS = {"approve": "approved", "reject": "rejected"}


def submit_leave(student_id, start_date, end_date, reason, supporting_document=None):
    """CW-OAP-01 row 1 (OA-UC-01)."""
    if not (reason or "").strip():
        raise ServiceError("A reason is required.")
    if start_date > end_date:
        raise ServiceError("The start date must not be after the end date.")

    with transaction.atomic():
        try:
            status = rules.transition(rules.START_STATE, "submit")
        except InvalidTransition as e:
            raise ServiceError(str(e)) from e
        fields = {}
        if supporting_document:
            fields["supporting_document"] = supporting_document
        application = LeaveApplication.objects.create(
            student_id=student_id,
            department=department_of(student_id),
            status=status,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
            **fields,
        )
        record_event(
            CASE_TYPE, application, rules.START_STATE, status, "submit", student_id
        )
        notify(student_id, "Leave application submitted", CASE_TYPE, application.id)
    return application


def decide_leave(application_id, action, actor_id, remark=""):
    """CW-OAP-01 rows 2-3 (OA-UC-03)."""
    if action not in _DECISION_WORDS:
        raise ServiceError("Action must be 'approve' or 'reject'.")

    with transaction.atomic():
        application = LeaveApplication.objects.select_for_update().get(
            pk=application_id
        )
        # Only the appropriate HoD sees the application at all (AFR-OAP-011).
        actor_department = department_of(actor_id)
        if not actor_department or actor_department != application.department:
            raise LeaveApplication.DoesNotExist
        if actor_id == application.student_id:
            raise ServiceError("You cannot decide your own application.")

        from_state = application.status
        try:
            application.status = rules.transition(from_state, action)
        except InvalidTransition as e:
            raise ServiceError(str(e)) from e
        application.decided_by_id = actor_id
        application.decided_at = timezone.now()
        application.decision_remark = remark
        application.save()

        record_event(
            CASE_TYPE, application, from_state, application.status, action,
            actor_id, remark,
        )
        notify(
            application.student_id,
            f"Your leave application was {_DECISION_WORDS[action]}",
            CASE_TYPE,
            application.id,
        )
    return application
