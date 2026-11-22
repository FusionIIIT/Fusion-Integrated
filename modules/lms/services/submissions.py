"""Assignment submission service operations."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied
from django.utils import timezone

from modules.lms.domain.constants import AssignmentStatus, CourseRole
from modules.lms.domain.rules import is_submission_ontime
from modules.lms.domain.validators import validate_submission_payload
from modules.lms.models import Assignment, AssignmentSubmission
from modules.lms.selectors.scoping import get_course_membership


def submit_assignment(
    assignment_id: int,
    submission_type: str,
    content_text: str | None,
    content_link: str | None,
    file_attachment: Any,
    principal: Any,
) -> AssignmentSubmission:
    """Submits student work conforming to assignment configuration
    before the due date (BR-LMS-012, 013).
    """
    user_id = getattr(principal, "user_id", None) or getattr(principal, "erp_user_id", None)
    if user_id is None:
        raise PermissionDenied("Authentication required to submit assignments.")

    assignment = Assignment.objects.filter(id=assignment_id).first()
    if not assignment:
        raise ValueError("Assignment does not exist.")

    membership = get_course_membership(assignment.course_id, user_id)
    if not membership or membership.role != CourseRole.STUDENT:
        raise PermissionDenied("Only registered course students may submit work.")

    now = timezone.now()
    if assignment.status not in (AssignmentStatus.PUBLISHED, AssignmentStatus.CLOSED):
        raise PermissionDenied("Submissions are not accepted for unreleased assignments.")

    # BR-LMS-013: Baseline on-time submission enforcement
    if not is_submission_ontime(now, assignment.due_date):
        raise ValueError("Assignment deadline has passed. Submissions are closed.")

    # BR-LMS-012: Submission-type conformity
    if submission_type != assignment.submission_type:
        raise ValueError(
            f"Submission type must match assignment configuration ({assignment.submission_type})."
        )

    validate_submission_payload(
        submission_type=submission_type,
        content_text=content_text,
        content_link=content_link,
        has_file=file_attachment is not None,
    )

    # Baseline single submission: if a submission exists, update it or raise error.
    # In baseline, we update the existing submission attempt record or create attempt 1.
    submission, created = AssignmentSubmission.objects.get_or_create(
        assignment=assignment,
        student_id=user_id,
        defaults={
            "submission_type": submission_type,
            "content_text": content_text or "",
            "content_link": content_link or "",
            "file_attachment": file_attachment,
            "attempt_number": 1,
        },
    )
    if not created:
        submission.submission_type = submission_type
        submission.content_text = content_text or ""
        submission.content_link = content_link or ""
        if file_attachment is not None:
            submission.file_attachment = file_attachment
        submission.submitted_at = now
        submission.save()

    return submission
