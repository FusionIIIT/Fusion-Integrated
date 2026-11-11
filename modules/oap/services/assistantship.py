from django.db import transaction
from django.utils import timezone

from modules.oap.domain import assistantship as rules
from modules.oap.domain.eligibility import is_pg
from modules.oap.domain.errors import InvalidTransition
from modules.oap.models import AssistantshipClaim, SupervisorVerification
from modules.oap.services.common import (
    ServiceError,
    department_of,
    directory_user,
    notify,
    record_event,
)
from modules.oap.services.records import resolve_supervisors

CASE_TYPE = "assistantship"

_DECISION_WORDS = {"approve": "approved", "reject": "rejected"}


def _transition(state, action):
    try:
        return rules.transition(state, action)
    except InvalidTransition as e:
        raise ServiceError(str(e)) from e


def _require_same_department(claim, actor_id):
    """Department Administrator / HoD act only within the claim's department."""
    actor_department = department_of(actor_id)
    if not actor_department or actor_department != claim.department:
        raise AssistantshipClaim.DoesNotExist


def submit_claim(student_id, claim_period=""):
    """CW-OAP-04 row 1 (OA-UC-31). PG students only (OA-BR-41)."""
    user = directory_user(student_id)
    if not is_pg(getattr(user, "programme", None)):
        raise ServiceError("Only PG students can submit an assistantship claim.")

    thesis_id, ta_id = resolve_supervisors(student_id)
    try:
        status = rules.submit(
            rules.START_STATE, thesis_id is not None, ta_id is not None
        )
    except InvalidTransition as e:  # OA-UC-31 E1: no claim is created.
        raise ServiceError(str(e)) from e

    with transaction.atomic():
        claim = AssistantshipClaim.objects.create(
            student_id=student_id,
            department=department_of(student_id),
            status=status,
            claim_period=claim_period,
            thesis_supervisor_id=thesis_id,
            ta_supervisor_id=ta_id,
        )
        record_event(CASE_TYPE, claim, rules.START_STATE, status, "submit", student_id)
        notify(student_id, "Assistantship claim submitted", CASE_TYPE, claim.id)
        # Routing to the supervisors (AFR-OAP-034).
        for supervisor_id in {thesis_id, ta_id}:
            notify(
                supervisor_id,
                "An assistantship claim awaits your verification",
                CASE_TYPE,
                claim.id,
            )
    return claim


def verify_claim(claim_id, role, actor_id, remark=""):
    """CW-OAP-04 rows 2-3 (OA-UC-33). The two roles stay separate verifications
    (OA-BR-42, OA-BR-52)."""
    if role not in rules.ROLES:
        raise ServiceError(f"Unknown supervisor role: '{role}'.")

    with transaction.atomic():
        claim = AssistantshipClaim.objects.select_for_update().get(pk=claim_id)
        expected = (
            claim.thesis_supervisor_id
            if role == rules.ROLE_THESIS
            else claim.ta_supervisor_id
        )
        if actor_id != expected:  # AFR-OAP-035
            raise ServiceError("You are not the assigned supervisor for this role.")

        already = set(claim.verifications.values_list("role", flat=True))
        from_state = claim.status
        try:
            claim.status = rules.verify(from_state, already, role)
        except InvalidTransition as e:
            raise ServiceError(str(e)) from e

        SupervisorVerification.objects.create(
            claim=claim, role=role, verified_by_id=actor_id, remark=remark
        )
        claim.save()

        record_event(
            CASE_TYPE, claim, from_state, claim.status, "verify_" + role,
            actor_id, remark,
        )
        if claim.status == rules.AWAITING_DEPARTMENT:
            notify(
                claim.student_id,
                "Both supervisors have verified your claim",
                CASE_TYPE,
                claim.id,
            )
    return claim


def forward_claim(claim_id, actor_id, remark=""):
    """CW-OAP-04 row 4 (OA-UC-34)."""
    with transaction.atomic():
        claim = AssistantshipClaim.objects.select_for_update().get(pk=claim_id)
        _require_same_department(claim, actor_id)

        from_state = claim.status
        claim.status = _transition(from_state, "forward")
        claim.department_reviewed_by_id = actor_id
        claim.save()

        record_event(
            CASE_TYPE, claim, from_state, claim.status, "forward", actor_id, remark
        )
        notify(
            claim.student_id,
            "Your claim was forwarded to the HoD",
            CASE_TYPE,
            claim.id,
        )
    return claim


def decide_claim(claim_id, action, actor_id, remark=""):
    """CW-OAP-04 rows 5-6 (OA-UC-35)."""
    if action not in _DECISION_WORDS:
        raise ServiceError("Action must be 'approve' or 'reject'.")

    with transaction.atomic():
        claim = AssistantshipClaim.objects.select_for_update().get(pk=claim_id)
        _require_same_department(claim, actor_id)

        from_state = claim.status
        claim.status = _transition(from_state, action)
        claim.decided_by_id = actor_id
        claim.decided_at = timezone.now()
        claim.decision_remark = remark
        claim.save()

        record_event(
            CASE_TYPE, claim, from_state, claim.status, action, actor_id, remark
        )
        notify(
            claim.student_id,
            f"Your assistantship claim was {_DECISION_WORDS[action]}",
            CASE_TYPE,
            claim.id,
        )
    return claim


def process_stipend(claim_id, actor_id, remark=""):
    """CW-OAP-04 row 7 (OA-UC-36, OA-BR-45). The Academic Administrator is
    institute-wide, so there is no department check."""
    with transaction.atomic():
        claim = AssistantshipClaim.objects.select_for_update().get(pk=claim_id)

        from_state = claim.status
        claim.status = _transition(from_state, "process_stipend")
        claim.stipend_processed_by_id = actor_id
        claim.save()

        record_event(
            CASE_TYPE, claim, from_state, claim.status, "process_stipend",
            actor_id, remark,
        )
        notify(
            claim.student_id,
            "Your stipend has been processed",
            CASE_TYPE,
            claim.id,
        )
    return claim
