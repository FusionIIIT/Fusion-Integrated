from django.db.models import QuerySet
from modules.lms.domain.constants import GradeStatus
from modules.lms.models import Grade, GradeAuditLog


def get_grade_for_submission(submission_id: int, is_staff: bool = False) -> Grade | None:
    """Returns the grade for a given submission. Non-staff only see released grades."""
    qs = Grade.objects.filter(submission_id=submission_id)
    if not is_staff:
        qs = qs.filter(status=GradeStatus.RELEASED)
    return qs.first()


def get_grade_audit_logs(grade_id: int) -> QuerySet:
    """Returns the audit logs for a given grade ordered by -changed_at."""
    return GradeAuditLog.objects.filter(
        grade_id=grade_id,
    ).order_by("-changed_at")
