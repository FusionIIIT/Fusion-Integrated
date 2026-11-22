"""Course Submissions write services (UC-LMS-010, BR-LMS-012, BR-LMS-013, BR-LMS-014)."""
from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, NotFoundError, PermissionDeniedError
from core.files.validators import sanitise_filename
from modules.courses.domain.errors import CourseDomainError
from modules.courses.domain.submissions import (
    SubmissionCreateDTO,
    validate_student_submitter,
)
from modules.courses.models import (
    CourseAssignment,
    CourseSubmission,
    CourseWorkspace,
)
from modules.courses.selectors import scoping

log = logging.getLogger("fusion.courses.submissions")


def submit_assignment(
    *,
    workspace_id: int,
    assignment_id: int,
    principal,
    submission_type: str = "file",
    content: str = "",
    link_url: str = "",
    file=None,
) -> CourseSubmission:
    """Creates or updates a student assignment submission (UC-LMS-010).

    Enforces:
    - BR-LMS-001: Workspace-scoped authorization.
    - BR-LMS-004: Only enrolled students can submit.
    - BR-LMS-010: Assignment must be published.
    - BR-LMS-012: Submission type validation.
    - BR-LMS-013: Baseline timing evaluation.
    - Resubmission support: Replaces latest submission, updates attempt counter,
      and cleans up replaced file storage objects.
    """
    raw_filename = getattr(file, "name", "") if file else ""
    file_size = getattr(file, "size", 0) if file else 0

    dto = SubmissionCreateDTO(
        submission_type=submission_type,
        content=content.strip(),
        link_url=link_url.strip(),
        has_file=file is not None,
        filename=raw_filename,
        file_size=file_size,
    )
    try:
        dto.validate()
    except CourseDomainError as exc:
        raise BadRequestError(str(exc)) from exc

    with transaction.atomic():
        workspace = CourseWorkspace.objects.filter(id=workspace_id).first()
        if not workspace:
            raise NotFoundError("Course workspace not found.")

        membership = scoping.get_workspace_membership(workspace, principal)
        if not membership:
            raise NotFoundError("Course workspace not found.")

        try:
            validate_student_submitter(membership.role)
        except CourseDomainError as exc:
            raise PermissionDeniedError(str(exc)) from exc

        assignment = CourseAssignment.objects.filter(
            id=assignment_id,
            workspace=workspace,
        ).first()
        if not assignment:
            raise NotFoundError("Course assignment not found.")

        if not assignment.is_published:
            raise BadRequestError("Cannot submit to an unpublished assignment.")

        now = timezone.now()
        is_late = bool(assignment.due_at and now > assignment.due_at)
        status_val = "late" if is_late else "submitted"

        filename = ""
        mime_type = ""
        saved_file = None
        if submission_type == "file" and file:
            filename = sanitise_filename(raw_filename, fallback="submission_upload")
            mime_type = getattr(file, "content_type", "application/octet-stream")
            saved_file = file

        existing = (
            CourseSubmission.objects.filter(
                assignment=assignment,
                student_id=principal.user_id,
            )
            .select_for_update()
            .first()
        )

        if existing:
            # Resubmission: clean up old file if replacing with a new file
            if saved_file and existing.file and existing.file != saved_file:
                existing.file.delete(save=False)

            existing.submission_type = submission_type
            if saved_file:
                existing.file = saved_file
                existing.filename = filename
                existing.file_size = file_size
                existing.mime_type = mime_type
            elif submission_type != "file" and existing.file:
                existing.file.delete(save=False)
                existing.file = None
                existing.filename = ""
                existing.file_size = 0
                existing.mime_type = ""

            existing.content = content.strip()
            existing.link_url = link_url.strip()
            existing.submitted_at = now
            existing.is_late = is_late
            existing.status = status_val
            existing.attempt_number += 1
            existing.save()

            log.info(
                "courses.submission.updated id=%d assignment=%d student=%d attempt=%d is_late=%s",
                existing.id,
                assignment.id,
                principal.user_id,
                existing.attempt_number,
                is_late,
            )
            return existing

        submission = CourseSubmission.objects.create(
            workspace=workspace,
            assignment=assignment,
            student_id=principal.user_id,
            submission_type=submission_type,
            file=saved_file,
            filename=filename,
            file_size=file_size,
            mime_type=mime_type,
            content=content.strip(),
            link_url=link_url.strip(),
            submitted_at=now,
            is_late=is_late,
            attempt_number=1,
            status=status_val,
        )

        log.info(
            "courses.submission.created id=%d assignment=%d student=%d attempt=1 is_late=%s",
            submission.id,
            assignment.id,
            principal.user_id,
            is_late,
        )
        return submission
