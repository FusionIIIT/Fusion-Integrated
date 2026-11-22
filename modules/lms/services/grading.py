"""Grading and grade release service operations."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from modules.lms.domain.constants import CourseRole, GradeStatus
from modules.lms.domain.state_machine import GradeFSM
from modules.lms.domain.validators import validate_grade_points
from modules.lms.models import AssignmentSubmission, GradeChangeAudit, SubmissionGrade
from modules.lms.selectors.scoping import get_course_membership, is_course_instructor


def grade_submission(
    submission_id: int,
    points_awarded: Decimal | float | int,
    feedback_text: str,
    principal: Any,
) -> SubmissionGrade:
    """Grades a submission and saves it in DRAFT mode (BR-LMS-015, BR-LMS-016)."""
    user_id = getattr(principal, "user_id", None) or getattr(principal, "erp_user_id", None) or 0
    submission = (
        AssignmentSubmission.objects.filter(id=submission_id).select_related("assignment").first()
    )
    if not submission:
        raise ValueError("Submission not found.")

    course_id = submission.assignment.course_id
    if not is_course_instructor(course_id, principal):
        membership = get_course_membership(course_id, user_id)
        if not membership or membership.role != CourseRole.TA or not membership.can_grade:
            raise PermissionDenied("You do not have grading authority for this course.")

    validate_grade_points(points_awarded, submission.assignment.points_possible)

    with transaction.atomic():
        grade, created = SubmissionGrade.objects.select_for_update().get_or_create(
            submission=submission,
            defaults={
                "points_awarded": Decimal(str(points_awarded)),
                "feedback_text": feedback_text or "",
                "status": GradeStatus.DRAFT,
                "graded_by": user_id,
            },
        )
        if not created:
            grade.points_awarded = Decimal(str(points_awarded))
            grade.feedback_text = feedback_text or ""
            grade.graded_by = user_id
            grade.save()

    return grade


def update_grade(
    submission_id: int,
    points_awarded: Decimal | float | int,
    feedback_text: str,
    reason: str,
    principal: Any,
) -> SubmissionGrade:
    """Updates an existing grade.
    If grade was already PUBLISHED, logs GradeChangeAudit (BR-LMS-019).
    """
    user_id = getattr(principal, "user_id", None) or getattr(principal, "erp_user_id", None) or 0
    submission = (
        AssignmentSubmission.objects.filter(id=submission_id).select_related("assignment").first()
    )
    if not submission:
        raise ValueError("Submission not found.")

    course_id = submission.assignment.course_id
    if not is_course_instructor(course_id, principal):
        membership = get_course_membership(course_id, user_id)
        if not membership or membership.role != CourseRole.TA or not membership.can_grade:
            raise PermissionDenied("You do not have grading authority for this course.")

    validate_grade_points(points_awarded, submission.assignment.points_possible)

    with transaction.atomic():
        grade = (
            SubmissionGrade.objects.select_for_update().filter(submission_id=submission_id).first()
        )
        if not grade:
            raise ValueError("No grade found to update.")

        old_points = grade.points_awarded
        old_feedback = grade.feedback_text
        was_published = grade.status == GradeStatus.PUBLISHED

        grade.points_awarded = Decimal(str(points_awarded))
        grade.feedback_text = feedback_text or ""
        grade.save(update_fields=["points_awarded", "feedback_text"])

        # BR-LMS-019: Post-release grade-change audit
        if was_published:
            GradeChangeAudit.objects.create(
                grade=grade,
                submission_id=submission_id,
                old_points=old_points,
                new_points=grade.points_awarded,
                old_feedback=old_feedback,
                new_feedback=grade.feedback_text,
                changed_by=user_id,
                reason=reason or "",
            )

    return grade


def publish_grades(
    assignment_id: int,
    submission_ids: list[int] | None,
    principal: Any,
) -> int:
    """Publishes draft grades to students. Strictly Faculty-only (BR-LMS-017)."""
    from modules.lms.models import Assignment

    assignment = Assignment.objects.filter(id=assignment_id).first()
    if not assignment or not is_course_instructor(assignment.course_id, principal):
        raise PermissionDenied("Only assigned instructors may publish grades.")

    user_id = getattr(principal, "user_id", None) or getattr(principal, "erp_user_id", None) or 0
    now = timezone.now()

    qs = SubmissionGrade.objects.filter(
        submission__assignment_id=assignment_id,
        status=GradeStatus.DRAFT,
    )
    if submission_ids:
        qs = qs.filter(submission_id__in=submission_ids)

    with transaction.atomic():
        return qs.update(
            status=GradeFSM.publish(GradeStatus.DRAFT),
            published_at=now,
            published_by=user_id,
        )
