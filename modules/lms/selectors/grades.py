"""Ownership- and membership-scoped LMS grading selectors."""
from __future__ import annotations

from typing import Any

from modules.directory import contracts as directory
from modules.lms.domain.entities import CourseRole, GradeStatus
from modules.lms.models import (
    CourseMembership,
    CourseSubmission,
    CourseSubmissionGrade,
)


def _grade_to_dict(
    g: CourseSubmissionGrade,
    grader_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": g.id,
        "submission_id": g.submission_id,
        "assignment_id": g.assignment_id,
        "student_user_id": g.student_user_id,
        "score": str(g.score),
        "points_possible": str(g.assignment.points_possible),
        "status": g.status,
        "graded_by_user_id": g.graded_by_user_id,
        "graded_by_name": grader_info.get("display_name", f"User {g.graded_by_user_id}")
        if grader_info
        else f"User {g.graded_by_user_id}",
        "graded_by_email": grader_info.get("email", "") if grader_info else "",
        "graded_at": g.graded_at.isoformat() if g.graded_at else "",
        "created_at": g.created_at.isoformat() if g.created_at else "",
        "updated_at": g.updated_at.isoformat() if g.updated_at else "",
    }


def get_submission_grade(
    *,
    principal,
    course_code: str,
    assignment_id: int,
    submission_id: int,
) -> dict[str, Any] | None:
    """Retrieve evaluation score and attribution for a submission.

    Enforces:
    - Actor is an authorized member of the course (BR-LMS-001, BR-LMS-002).
    - Observers cannot view grades (CFR-LMS-015, AFR-LMS-015.3, BR-LMS-003).
    - Students can only view their own released grade (BR-LMS-014, BR-LMS-016, AFR-LMS-011.2).
    - Faculty and TAs can view draft and released evaluations (CFR-LMS-010, AFR-LMS-014.2).
    """
    if principal is None:
        return None

    membership = (
        CourseMembership.objects.filter(course__code=course_code, user_id=principal.user_id)
        .select_related("course")
        .first()
    )
    if membership is None:
        return None

    # Observers cannot view grades or student data (CFR-LMS-015, AFR-LMS-015.3)
    if membership.role == CourseRole.OBSERVER:
        return None

    submission = (
        CourseSubmission.objects.filter(
            id=submission_id,
            assignment_id=assignment_id,
            assignment__course=membership.course,
        )
        .select_related("assignment")
        .first()
    )
    if submission is None:
        return None

    grade = (
        CourseSubmissionGrade.objects.filter(submission=submission)
        .select_related("assignment")
        .first()
    )
    if grade is None:
        return None

    # Students cannot view peer grades and cannot view draft grades (BR-LMS-014, BR-LMS-016)
    if membership.role == CourseRole.STUDENT:
        if submission.student_user_id != principal.user_id:
            return None
        if grade.status == GradeStatus.DRAFT:
            return None

    grader_facts = directory.get_users([grade.graded_by_user_id])
    grader_info = grader_facts.get(grade.graded_by_user_id)

    return _grade_to_dict(grade, grader_info=grader_info)
