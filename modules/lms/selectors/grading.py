"""Submission grading selectors."""

from __future__ import annotations

from typing import Any

from modules.lms.domain.constants import GradeStatus
from modules.lms.models import AssignmentSubmission, GradeChangeAudit, SubmissionGrade
from modules.lms.selectors.scoping import (
    has_course_access,
    is_course_instructor,
    is_course_observer,
    is_course_ta,
)


def get_submission_grade(submission_id: int, principal: Any) -> SubmissionGrade | None:
    submission = (
        AssignmentSubmission.objects.filter(id=submission_id).select_related("assignment").first()
    )
    if not submission or not has_course_access(submission.assignment.course_id, principal):
        return None

    if is_course_observer(submission.assignment.course_id, principal):
        return None

    is_staff = is_course_instructor(submission.assignment.course_id, principal) or is_course_ta(
        submission.assignment.course_id, principal
    )
    grade = SubmissionGrade.objects.filter(submission_id=submission_id).first()
    if not grade:
        return None

    if is_staff:
        return grade

    user_id = getattr(principal, "user_id", None) or getattr(principal, "erp_user_id", None)
    if submission.student_id == user_id and grade.status == GradeStatus.PUBLISHED:
        return grade

    return None


def list_course_grades(assignment_id: int, principal: Any) -> list[SubmissionGrade]:
    from modules.lms.models import Assignment

    assignment = Assignment.objects.filter(id=assignment_id).first()
    if not assignment or not has_course_access(assignment.course_id, principal):
        return []

    if is_course_observer(assignment.course_id, principal):
        return []

    is_staff = is_course_instructor(assignment.course_id, principal) or is_course_ta(
        assignment.course_id, principal
    )
    if not is_staff:
        return []

    return list(
        SubmissionGrade.objects.filter(
            submission__assignment_id=assignment_id,
        ).select_related("submission")
    )


def get_grade_audit_history(submission_id: int, principal: Any) -> list[GradeChangeAudit]:
    submission = (
        AssignmentSubmission.objects.filter(id=submission_id).select_related("assignment").first()
    )
    if not submission or not is_course_instructor(submission.assignment.course_id, principal):
        return []

    return list(
        GradeChangeAudit.objects.filter(submission_id=submission_id).order_by("-changed_at")
    )
