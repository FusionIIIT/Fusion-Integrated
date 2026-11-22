"""Assignment submission service operations."""

from __future__ import annotations

from typing import Any

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from core.files.validators import sanitise_filename
from modules.lms.domain.constants import AssignmentStatus, CourseRole
from modules.lms.domain.rules import is_submission_ontime
from modules.lms.domain.validators import validate_submission_payload
from modules.lms.models import Assignment, AssignmentSubmission
from modules.lms.selectors.scoping import get_course_membership


def _validate_submission_file(file_obj: Any) -> None:
    """Validates attachment size and sanitises filename for submissions."""
    max_bytes = 20 * 1024 * 1024
    if file_obj.size > max_bytes:
        raise BadRequestError("File size cannot exceed 20 MB; compress or share via Google Drive.")
    file_obj.name = sanitise_filename(file_obj.name, fallback="submission_upload")


def _check_submission_eligibility(assignment: Assignment, user_id: int) -> None:
    """Validates that student membership and assignment state permit submissions."""
    membership = get_course_membership(assignment.course_id, user_id)
    if not membership or membership.role != CourseRole.STUDENT:
        raise PermissionDeniedError("Only registered course students may submit work.")

    if assignment.status not in (AssignmentStatus.PUBLISHED, AssignmentStatus.CLOSED):
        raise PermissionDeniedError("Submissions are not accepted for unreleased assignments.")

    now = timezone.now()
    if not is_submission_ontime(now, assignment.due_date):
        raise ConflictError("Assignment deadline has passed. Submissions are closed.")


def submit_assignment(
    assignment_id: int,
    submission_type: str,
    content_text: str | None,
    content_link: str | None,
    file_attachment: Any,
    principal: Any,
) -> AssignmentSubmission:
    """Submits student work conforming to configuration and deadline (BR-LMS-012, BR-LMS-013)."""
    user_id = getattr(principal, "user_id", None) or getattr(principal, "erp_user_id", None)
    if user_id is None:
        raise PermissionDeniedError("Authentication required to submit assignments.")

    with transaction.atomic():
        assignment = Assignment.objects.select_for_update().filter(id=assignment_id).first()
        if not assignment:
            raise NotFoundError("Assignment does not exist.")

        _check_submission_eligibility(assignment, user_id)

        if submission_type != assignment.submission_type:
            raise BadRequestError(
                f"Submission type must match assignment configuration "
                f"({assignment.submission_type})."
            )

        if file_attachment is not None:
            _validate_submission_file(file_attachment)

        try:
            validate_submission_payload(
                submission_type=submission_type,
                content_text=content_text,
                content_link=content_link,
                has_file=file_attachment is not None,
            )
        except ValueError as exc:
            raise BadRequestError(str(exc)) from exc

        existing = (
            AssignmentSubmission.objects.select_for_update()
            .filter(assignment=assignment, student_id=user_id)
            .order_by("-attempt_number")
            .first()
        )
        next_attempt = (existing.attempt_number + 1) if existing else 1

        return AssignmentSubmission.objects.create(
            assignment=assignment,
            student_id=user_id,
            submission_type=submission_type,
            content_text=content_text or "",
            content_link=content_link or "",
            file_attachment=file_attachment,
            attempt_number=next_attempt,
        )
