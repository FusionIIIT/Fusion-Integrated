from django.db import transaction
from django.utils import timezone

from modules.oap.domain import nodues as rules
from modules.oap.domain.errors import InvalidTransition
from modules.oap.models import NoDuesClearance, NoDuesRequest
from modules.oap.services.common import (
    ServiceError,
    department_of,
    notify,
    record_event,
)

CASE_TYPE = "nodues"


def _results(request):
    return {c.domain_code: c.result for c in request.clearances.all()}


def submit_nodues(student_id):
    """CW-OAP-03 row 1 (OA-UC-21). One request goes to all seven authorities
    in parallel (AFR-OAP-023)."""
    with transaction.atomic():
        active = NoDuesRequest.objects.filter(student_id=student_id).exclude(
            status__in=rules.TERMINAL_STATES
        )
        if active.exists():
            raise ServiceError("You already have an active no-dues request.")
        try:
            status = rules.submit(rules.START_STATE)
        except InvalidTransition as e:
            raise ServiceError(str(e)) from e
        obj = NoDuesRequest.objects.create(
            student_id=student_id,
            department=department_of(student_id),
            status=status,
        )
        NoDuesClearance.objects.bulk_create(
            [
                NoDuesClearance(
                    request=obj, domain_code=code, result=rules.RESULT_PENDING
                )
                for code in rules.DOMAIN_CODES
            ]
        )
        record_event(CASE_TYPE, obj, rules.START_STATE, status, "submit", student_id)
        notify(student_id, "No-dues request submitted", CASE_TYPE, obj.id)
    return obj


def record_clearance(request_id, domain_code, result, actor_id, remark=""):
    """CW-OAP-03 rows 2-4 (OA-UC-22). An authority records only its own domain."""
    if domain_code not in rules.DOMAIN_CODES:
        raise ServiceError(f"Unknown domain: '{domain_code}'.")
    if result not in (rules.RESULT_CLEAR, rules.RESULT_DUES):
        raise ServiceError("Result must be 'Clear' or 'Dues Outstanding'.")

    with transaction.atomic():
        obj = NoDuesRequest.objects.select_for_update().get(pk=request_id)

        # Respective Department: only the student's own department (OA-BR-31).
        if domain_code == "department":
            actor_department = department_of(actor_id)
            if not actor_department or actor_department != obj.department:
                raise NoDuesRequest.DoesNotExist

        row = obj.clearances.select_for_update().get(domain_code=domain_code)
        if row.result != rules.RESULT_PENDING:
            raise ServiceError("This domain has already recorded its result.")

        from_state = obj.status
        row.result = result
        row.remark = remark
        row.recorded_by_id = actor_id
        row.recorded_at = timezone.now()
        row.save()  # OA-BR-32: only this domain's row changes.

        try:
            obj.status = rules.state_after_results(from_state, _results(obj))
        except InvalidTransition as e:
            raise ServiceError(str(e)) from e
        obj.save()

        record_event(
            CASE_TYPE, obj, from_state, obj.status, "verify_" + domain_code,
            actor_id, remark,
        )
        if obj.status != rules.IN_PROGRESS:
            notify(
                obj.student_id,
                "No-dues verification is complete",
                CASE_TYPE,
                obj.id,
            )
    return obj


def finalize_nodues(request_id, actor_id):
    """CW-OAP-03 row 5 (OA-UC-23, OA-BR-33)."""
    with transaction.atomic():
        obj = NoDuesRequest.objects.select_for_update().get(pk=request_id)
        from_state = obj.status
        try:
            obj.status = rules.finalize(from_state, _results(obj))
        except InvalidTransition as e:
            raise ServiceError(str(e)) from e
        obj.finalized_by_id = actor_id
        obj.finalized_at = timezone.now()
        obj.certificate_number = f"NDC-{obj.id:06d}"
        obj.save()

        record_event(CASE_TYPE, obj, from_state, obj.status, "finalize", actor_id)
        notify(
            obj.student_id,
            "Your no-dues certificate is available",
            CASE_TYPE,
            obj.id,
        )
    return obj


def certificate_for(request_id, student_id):
    """OA-BR-34: only the owner, and only once finalized."""
    obj = NoDuesRequest.objects.get(pk=request_id)
    if obj.student_id != student_id:
        raise NoDuesRequest.DoesNotExist
    if obj.status != rules.FINALIZED:
        raise ServiceError("The certificate is not available for this request.")
    return obj
