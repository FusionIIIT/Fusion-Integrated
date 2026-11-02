from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone
from modules.lms.domain.constants import GradeAction, GradeStatus, Role
from modules.lms.models import Grade, GradeAuditLog


def save_draft_grade(
    submission_id: int,
    assessor_user_id: int,
    assessor_role: str,
    points_awarded: int | None = None,
    feedback_text: str = "",
) -> Grade:
    grade, created = Grade.objects.get_or_create(
        submission_id=submission_id,
        defaults={
            "assessor_user_id": assessor_user_id,
            "assessor_role": assessor_role,
        },
    )
    if not created and grade.status == GradeStatus.RELEASED:
        raise PermissionDenied(
            "Grade has already been released and cannot be modified pending policy clarification (ISS-LMS-006)."
        )
    grade.assessor_user_id = assessor_user_id
    grade.assessor_role = assessor_role
    grade.points_awarded = points_awarded
    grade.feedback_text = feedback_text
    grade.status = GradeStatus.DRAFT
    grade.save()
    return grade


def release_grade(
    submission_id: int,
    assessor_user_id: int,
    assessor_role: str,
    points_awarded: int,
    feedback_text: str = "",
    reason: str = "initial grade release",
) -> Grade:
    if assessor_role != Role.INSTRUCTOR:
        raise PermissionDenied("Only instructors can release grades.")

    with transaction.atomic():
        grade, created = Grade.objects.get_or_create(
            submission_id=submission_id,
            defaults={
                "assessor_user_id": assessor_user_id,
                "assessor_role": assessor_role,
            },
        )
        if not created and grade.status == GradeStatus.RELEASED:
            raise PermissionDenied(
                "Grade has already been released and cannot be re-released pending policy clarification (ISS-LMS-006)."
            )

        prev_points = grade.points_awarded
        prev_feedback = grade.feedback_text
        grade.points_awarded = points_awarded
        grade.feedback_text = feedback_text
        grade.status = GradeStatus.RELEASED
        grade.released_at = timezone.now()
        grade.released_by_user_id = assessor_user_id
        grade.assessor_user_id = assessor_user_id
        grade.assessor_role = assessor_role
        grade.save()
        GradeAuditLog.objects.create(
            grade=grade,
            assessor_user_id=assessor_user_id,
            action=GradeAction.RELEASED,
            previous_points=prev_points,
            new_points=points_awarded,
            previous_feedback=prev_feedback,
            new_feedback=feedback_text,
            reason=reason,
        )
    return grade


def modify_released_grade(
    grade_id: int,
    modifier_user_id: int,
    new_points: int | None = None,
    new_feedback: str = "",
    reason: str = "",
) -> Grade:
    raise PermissionDenied(
        "Post-release grade modification is pending policy clarification (ISS-LMS-006)."
    )
