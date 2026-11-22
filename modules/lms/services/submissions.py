"""Transactional student submission handling."""
from __future__ import annotations

from typing import Any

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.lms.domain.entities import (
    CourseRole,
    DeadlineWindowStatus,
    SubmissionStatus,
    validate_submission_details,
)
from modules.lms.domain.errors import LMSRuleError
from modules.lms.models import (
    CourseAssignment,
    CourseMembership,
    CourseSubmission,
)
from modules.lms.selectors.deadlines import calculate_deadline_info
from modules.lms.services.authz import require

P_SUBMIT_WORK = "lms.submission.submit"


@transaction.atomic
def create_submission(
    *,
    actor,
    course_code: str,
    assignment_id: int,
    submission_type: str,
    file: Any = None,
    file_name: str = "",
    file_size: int | None = None,
    content_text: str = "",
    link_url: str = "",
) -> CourseSubmission:
    """Submit student assignment work (CFR-LMS-008, AFR-LMS-008.1, AFR-LMS-008.2).

    Enforces:
    - Actor holds `lms.submission.submit` permission.
    - Actor is an enrolled Student in the course (BR-LMS-001, BR-LMS-004).
    - Assignment is published and accessible.
    - Submission window is open or late-allowed (BR-LMS-013, CFR-LMS-008).
    - Submission type conforms to assignment's configured type (BR-LMS-012).
    - Attempt history is updated with incremented attempt number.
    """
    require(actor, P_SUBMIT_WORK)

    membership = (
        CourseMembership.objects.filter(course__code=course_code, user_id=actor.user_id)
        .select_related("course")
        .first()
    )
    if membership is None:
        raise NotFoundError("Course not found or you are not enrolled in it.")

    if membership.role != CourseRole.STUDENT:
        raise PermissionDeniedError("Only enrolled students can submit assignment work.")

    assignment = (
        CourseAssignment.objects.filter(id=assignment_id, course=membership.course)
        .select_for_update()
        .first()
    )
    if assignment is None:
        raise NotFoundError("Course assignment not found.")

    now = timezone.now()
    if assignment.status == "draft":
        raise ConflictError("Assignment is in draft state and not open for submissions.")
    if assignment.status == "scheduled" and (
        not assignment.release_at or assignment.release_at > now
    ):
        raise ConflictError("Assignment is scheduled and not yet released for submissions.")

    # Validate submission window using Implementation 5 deadline engine
    dl_info = calculate_deadline_info(assignment, student_user_id=actor.user_id)
    window_status = dl_info["window_status"]

    if window_status == DeadlineWindowStatus.NOT_OPEN:
        raise ConflictError(
            "Assignment submission window is not open.",
            code="submission_window_not_open",
        )
    if window_status == DeadlineWindowStatus.CLOSED:
        raise ConflictError(
            "Submission deadline window is closed. Submissions are no longer accepted.",
            code="submission_window_closed",
        )

    # Determine submission status (on-time vs late)
    if window_status == DeadlineWindowStatus.OPEN:
        submission_status = SubmissionStatus.SUBMITTED
    elif window_status == DeadlineWindowStatus.LATE_ALLOWED:
        submission_status = SubmissionStatus.LATE
    else:
        submission_status = SubmissionStatus.SUBMITTED

    # Validate submission parameters against assignment configuration (BR-LMS-012)
    try:
        validate_submission_details(
            assignment_submission_type=assignment.submission_type,
            submission_type=submission_type,
            file=file,
            content_text=content_text,
            link_url=link_url,
        )
    except LMSRuleError as exc:
        raise ConflictError(str(exc), code="submission_validation_failed") from exc

    f_name = file_name.strip() if file_name else ""
    f_size = file_size
    if file and hasattr(file, "name"):
        if not f_name:
            f_name = file.name
        if f_size is None and hasattr(file, "size"):
            f_size = file.size

    # Manage attempt history: mark previous submissions as not latest
    prev_submissions = CourseSubmission.objects.filter(
        assignment=assignment,
        student_user_id=actor.user_id,
    )
    attempt_number = prev_submissions.count() + 1
    prev_submissions.filter(is_latest=True).update(is_latest=False)

    return CourseSubmission.objects.create(
        assignment=assignment,
        student_user_id=actor.user_id,
        submission_type=submission_type,
        status=submission_status,
        submitted_at=now,
        file=file,
        file_name=f_name if submission_type == "file" else "",
        file_size=f_size if submission_type == "file" else None,
        content_text=content_text.strip() if submission_type == "text" else "",
        link_url=link_url.strip() if submission_type == "link" else "",
        attempt_number=attempt_number,
        is_latest=True,
    )
