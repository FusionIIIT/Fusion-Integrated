"""Assignment submission selectors."""

from __future__ import annotations

from typing import Any

from modules.lms.models import Assignment, AssignmentSubmission
from modules.lms.selectors.scoping import (
    has_course_access,
    is_course_instructor,
    is_course_observer,
    is_course_ta,
)


def list_course_submissions(assignment_id: int, principal: Any) -> list[AssignmentSubmission]:
    assignment = Assignment.objects.filter(id=assignment_id).first()
    if not assignment or not has_course_access(assignment.course_id, principal):
        return []

    # Observers are strictly excluded from student submissions (BR-LMS-003, AFR-LMS-015.2).
    if is_course_observer(assignment.course_id, principal):
        return []

    is_staff = is_course_instructor(assignment.course_id, principal) or is_course_ta(
        assignment.course_id, principal
    )
    if is_staff:
        return list(
            AssignmentSubmission.objects.filter(assignment_id=assignment_id).order_by(
                "submitted_at"
            )
        )

    user_id = getattr(principal, "user_id", None) or getattr(principal, "erp_user_id", None)
    if user_id is None:
        return []
    return list(
        AssignmentSubmission.objects.filter(assignment_id=assignment_id, student_id=user_id)
    )


def get_student_submission(assignment_id: int, principal: Any) -> AssignmentSubmission | None:
    assignment = Assignment.objects.filter(id=assignment_id).first()
    if not assignment or not has_course_access(assignment.course_id, principal):
        return None

    if is_course_observer(assignment.course_id, principal):
        return None

    user_id = getattr(principal, "user_id", None) or getattr(principal, "erp_user_id", None)
    if user_id is None:
        return None

    return AssignmentSubmission.objects.filter(
        assignment_id=assignment_id, student_id=user_id
    ).first()


def get_submission_by_id(submission_id: int, principal: Any) -> AssignmentSubmission | None:
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
    if is_staff:
        return submission

    user_id = getattr(principal, "user_id", None) or getattr(principal, "erp_user_id", None)
    if submission.student_id == user_id:
        return submission

    return None
