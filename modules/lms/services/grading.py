"""Grading and grade release services (UC-LMS-012, UC-LMS-013, BR-LMS-015, BR-LMS-019)."""
from __future__ import annotations

from decimal import Decimal
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied
from modules.lms.models import (
    Assignment,
    AssignmentSubmission,
    SubmissionGrade,
    GradeChangeAudit,
    CourseMembership,
)


def grade_submission(
    submission: AssignmentSubmission,
    points: Decimal | None = None,
    feedback: str = "",
    grader_user_id: int = 0,
    grader_role: str = "",
    grader_name: str = "",
    change_reason: str = "",
    points_awarded: Decimal | None = None,
) -> SubmissionGrade:
    """Record or update a submission grade with attribution (BR-LMS-015).

    If grade was already released, record an audit entry (BR-LMS-019).
    """
    if points is None and points_awarded is not None:
        points = points_awarded
    if points is None:
        raise ValidationError("Points awarded is required.")

    if points < 0:
        raise ValidationError("Points awarded cannot be negative.")
    if points > submission.assignment.points_possible:
        raise ValidationError(
            f"Points awarded ({points}) exceeds points possible ({submission.assignment.points_possible})."
        )

    grade = getattr(submission, "grade", None)
    if grade is None:
        # Create initial grade in draft state (BR-LMS-016)
        grade = SubmissionGrade.objects.create(
            submission=submission,
            points_awarded=points,
            feedback=feedback,
            status="draft",
            graded_by_user_id=grader_user_id,
            graded_by_role=grader_role,
            graded_by_name=grader_name,
        )
    else:
        # If grade was already released, create audit log before updating (BR-LMS-019)
        if grade.status == "released":
            GradeChangeAudit.objects.create(
                grade=grade,
                previous_points=grade.points_awarded,
                new_points=points,
                previous_feedback=grade.feedback,
                new_feedback=feedback,
                changed_by_user_id=grader_user_id,
                changed_by_name=grader_name,
                change_reason=change_reason or "Grade revised post-release",
            )

        grade.points_awarded = points
        grade.feedback = feedback
        grade.graded_by_user_id = grader_user_id
        grade.graded_by_role = grader_role
        grade.graded_by_name = grader_name
        grade.save()

    return grade


def release_assignment_grades(assignment: Assignment, faculty_user_id: int) -> int:
    """Release all draft grades for an assignment to students (BR-LMS-017)."""
    now = timezone.now()
    updated = SubmissionGrade.objects.filter(
        submission__assignment=assignment,
        status="draft",
    ).update(
        status="released",
        released_at=now,
        released_by_user_id=faculty_user_id,
    )
    return updated


def release_single_grade(grade: SubmissionGrade, faculty_user_id: int) -> SubmissionGrade:
    """Release a single student's draft grade."""
    grade.status = "released"
    grade.released_at = timezone.now()
    grade.released_by_user_id = faculty_user_id
    grade.save()
    return grade
