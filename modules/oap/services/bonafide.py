from django.db import transaction
from django.utils import timezone

from modules.oap.domain import bonafide as rules
from modules.oap.domain.errors import InvalidTransition
from modules.oap.models import BonafideRequest
from modules.oap.services.common import (
    ServiceError,
    department_of,
    notify,
    record_event,
)

CASE_TYPE = "bonafide"

_DECISION_WORDS = {"approve": "approved", "reject": "rejected"}


def submit_bonafide(student_id, purpose=""):
    """CW-OAP-02 row 1 (OA-UC-11)."""
    with transaction.atomic():
        try:
            status = rules.transition(rules.START_STATE, "submit")
        except InvalidTransition as e:
            raise ServiceError(str(e)) from e
        obj = BonafideRequest.objects.create(
            student_id=student_id,
            department=department_of(student_id),
            status=status,
            purpose=purpose,
        )
        record_event(CASE_TYPE, obj, rules.START_STATE, status, "submit", student_id)
        notify(student_id, "Bonafide request submitted", CASE_TYPE, obj.id)
    return obj


def decide_bonafide(request_id, action, actor_id, remark=""):
    """CW-OAP-02 rows 2-3 (OA-UC-12). The Academic Administrator decides
    requests from every department (OA-BR-21), so there is no department check."""
    if action not in _DECISION_WORDS:
        raise ServiceError("Action must be 'approve' or 'reject'.")

    with transaction.atomic():
        obj = BonafideRequest.objects.select_for_update().get(pk=request_id)
        from_state = obj.status
        try:
            obj.status = rules.transition(from_state, action)
        except InvalidTransition as e:
            raise ServiceError(str(e)) from e
        obj.decided_by_id = actor_id
        obj.decided_at = timezone.now()
        obj.decision_remark = remark
        if action == "approve":
            obj.certificate_number = f"BON-{obj.id:06d}"
        obj.save()

        record_event(
            CASE_TYPE, obj, from_state, obj.status, action, actor_id, remark
        )
        notify(
            obj.student_id,
            f"Your bonafide request was {_DECISION_WORDS[action]}",
            CASE_TYPE,
            obj.id,
        )
        if action == "approve":
            notify(
                obj.student_id,
                "Your bonafide certificate is available",
                CASE_TYPE,
                obj.id,
            )
    return obj


def certificate_for(request_id, student_id):
    """Only the owner may fetch the certificate, and only once approved (OA-BR-22)."""
    obj = BonafideRequest.objects.get(pk=request_id)
    if obj.student_id != student_id:
        raise BonafideRequest.DoesNotExist
    if obj.status != rules.APPROVED:
        raise ServiceError("The certificate is not available for this request.")
    return obj
