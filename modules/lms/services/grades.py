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
    GradeAuditLog,
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

    existing_grade = CourseSubmissionGrade.objects.filter(submission=submission).first()
    if existing_grade is not None and existing_grade.status == GradeStatus.RELEASED:
        GradeAuditLog.objects.create(
            submission=submission,
            old_score=existing_grade.score,
            new_score=validated_score,
            actor_user_id=actor.user_id,
        )

    now = timezone.now()
    target_status = (
        GradeStatus.RELEASED
        if (existing_grade and existing_grade.status == GradeStatus.RELEASED)
        else GradeStatus.DRAFT
    )

    grade, _created = CourseSubmissionGrade.objects.update_or_create(
        submission=submission,
        defaults={
            "assignment": assignment,
            "student_user_id": submission.student_user_id,
            "score": validated_score,
            "status": target_status,
            "graded_by_user_id": actor.user_id,
            "graded_at": now,
        },
    )

    return grade


@transaction.atomic
def release_assignment_grades(
    *,
    actor,
    course_code: str,
    assignment_id: int,
) -> int:
    """Release all draft grades for a course assignment to students.

    Enforces:
    - Actor holds `lms.grade.grade` permission.
    - Actor is Faculty for the course (BR-LMS-017, UC-LMS-013).
    - Assignment belongs to the specified course.
    - Transitions all draft grades for this assignment to RELEASED status.
    """
    require(actor, P_GRADE)

    membership = (
        CourseMembership.objects.filter(course__code=course_code, user_id=actor.user_id)
        .select_related("course")
        .first()
    )
    if membership is None:
        raise NotFoundError("Course not found or actor is not enrolled.")

    if membership.role != CourseRole.FACULTY:
        raise PermissionDeniedError(
            "Only Faculty assigned to this course can release assignment grades."
        )

    assignment = CourseAssignment.objects.filter(
        id=assignment_id, course=membership.course
    ).first()
    if assignment is None:
        raise NotFoundError("Course assignment not found.")

    return CourseSubmissionGrade.objects.filter(
        assignment=assignment,
        status=GradeStatus.DRAFT,
    ).update(status=GradeStatus.RELEASED)

