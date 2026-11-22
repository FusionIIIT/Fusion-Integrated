"""LMS Course Assignment grading transactional service."""
from __future__ import annotations

from typing import Any

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.lms.domain.entities import CourseRole, GradeStatus, validate_evaluation_score
from modules.lms.domain.errors import LMSRuleError
from modules.lms.models import (
    CourseAssignment,
    CourseMembership,
    CourseSubmission,
    CourseSubmissionGrade,
)
from modules.lms.services.authz import require

P_GRADE = "lms.grade.grade"


@transaction.atomic
def record_submission_grade(
    *,
    actor,
    course_code: str,
    assignment_id: int,
    submission_id: int,
    score: Any,
) -> CourseSubmissionGrade:
    """Evaluate and record/update score for a student submission.

    Enforces:
    - Actor holds `lms.grade.grade` permission.
    - Actor is Faculty or TA enrolled in the course (BR-LMS-004, BR-LMS-015, CFR-LMS-010).
    - Assignment belongs to the specified course and submission belongs to the assignment.
    - Score is validated against assignment's points_possible (CFR-LMS-010, AFR-LMS-010.1).
    - Grade status is set to Draft (CFR-LMS-011, AFR-LMS-011.1, BR-LMS-016).
    - Grader attribution is recorded with actor.user_id and timestamp (AFR-LMS-010.3, BR-LMS-015).
    """
    require(actor, P_GRADE)

    membership = (
        CourseMembership.objects.filter(course__code=course_code, user_id=actor.user_id)
        .select_related("course")
        .first()
    )
    if membership is None:
        raise NotFoundError("Course not found or actor is not enrolled.")

    if membership.role not in {CourseRole.FACULTY, CourseRole.TA}:
        raise PermissionDeniedError(
            "Only Faculty and Teaching Assistants for this course can grade submissions."
        )

    assignment = CourseAssignment.objects.filter(
        id=assignment_id, course=membership.course
    ).first()
    if assignment is None:
        raise NotFoundError("Course assignment not found.")

    submission = CourseSubmission.objects.filter(
        id=submission_id, assignment=assignment
    ).first()
    if submission is None:
        raise NotFoundError("Student submission not found for this assignment.")

    # Validate score against points_possible and domain constraints
    try:
        validated_score = validate_evaluation_score(
            score=score,
            points_possible=assignment.points_possible,
        )
    except LMSRuleError as exc:
        raise ConflictError(str(exc), code="invalid_score") from exc

    now = timezone.now()

    grade, _created = CourseSubmissionGrade.objects.update_or_create(
        submission=submission,
        defaults={
            "assignment": assignment,
            "student_user_id": submission.student_user_id,
            "score": validated_score,
            "status": GradeStatus.DRAFT,
            "graded_by_user_id": actor.user_id,
            "graded_at": now,
        },
    )

    return grade
