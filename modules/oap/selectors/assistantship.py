from django.db.models import Q, QuerySet

from modules.oap.domain import constants as c
from modules.oap.models.assistantship import AssistantshipClaim


def get_student_claims(user_id: int) -> QuerySet[AssistantshipClaim]:
    return AssistantshipClaim.objects.filter(user_id=user_id).prefetch_related("supervisor_verifications")


def get_claim_by_id(claim_id: int) -> AssistantshipClaim | None:
    return AssistantshipClaim.objects.filter(id=claim_id).prefetch_related("supervisor_verifications").first()


def get_claims_for_supervisor(supervisor_user_id: int) -> QuerySet[AssistantshipClaim]:
    """Returns claims where the faculty member is either Thesis Supervisor or TA Supervisor."""
    return AssistantshipClaim.objects.filter(
        Q(thesis_supervisor_user_id=supervisor_user_id) | Q(ta_supervisor_user_id=supervisor_user_id)
    ).prefetch_related("supervisor_verifications")


def get_claims_for_dept_review(department: str) -> QuerySet[AssistantshipClaim]:
    return AssistantshipClaim.objects.filter(
        department=department,
        status=c.ASSISTANTSHIP_AWAITING_DEPT_REVIEW,
    ).prefetch_related("supervisor_verifications")


def get_claims_for_hod(department: str) -> QuerySet[AssistantshipClaim]:
    return AssistantshipClaim.objects.filter(
        department=department,
        status=c.ASSISTANTSHIP_AWAITING_HOD_DECISION,
    ).prefetch_related("supervisor_verifications")


def get_approved_claims_for_disbursement() -> QuerySet[AssistantshipClaim]:
    return AssistantshipClaim.objects.filter(
        status=c.ASSISTANTSHIP_APPROVED_AWAITING_STIPEND,
    ).prefetch_related("supervisor_verifications")
