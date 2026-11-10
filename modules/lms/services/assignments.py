"""Transactional Course Assignments writes and scheduled release handling."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.lms.domain.entities import (
    AssignmentStatus,
    CourseRole,
    SubmissionType,
    validate_assignment_details,
)
from modules.lms.domain.errors import LMSRuleError
from modules.lms.models import CourseAssignment, CourseMembership
from modules.lms.services.authz import require

P_MANAGE_ASSIGNMENT = "lms.assignment.manage"


@transaction.atomic
def create_course_assignment(
    *,
    actor,
    course_code: str,
    title: str,
    instructions: str = "",
    submission_type: str = SubmissionType.FILE,
    points_possible: Decimal | float | int | str = Decimal("100.00"),
    status: str = AssignmentStatus.DRAFT,
    due_at: datetime | None = None,
    release_at: datetime | None = None,
    file: Any = None,
    file_name: str = "",
    file_size: int | None = None,
) -> CourseAssignment:
    """Create a course assignment under CFR-LMS-006 and UC-LMS-007.

    Restricted strictly to Faculty assigned to this course (AFR-LMS-006.1, BR-LMS-004).
    TAs, Students, and Observers are explicitly prevented from authoring assignments
    (AFR-LMS-014.3, AFR-LMS-015.4, BR-LMS-004).
    """
    require(actor, P_MANAGE_ASSIGNMENT)

    membership = (
        CourseMembership.objects.filter(course__code=course_code, user_id=actor.user_id)
        .select_related("course")
        .first()
    )
    if membership is None:
        raise NotFoundError("Course not found or you are not linked to it.")

    if membership.role == CourseRole.TA:
        raise PermissionDeniedError(
            "Teaching Assistants are not permitted to author assignments."
        )
    if membership.role == CourseRole.STUDENT:
        raise PermissionDeniedError("Students cannot create course assignments.")
    if membership.role == CourseRole.OBSERVER:
        raise PermissionDeniedError(
            "Observers have read-only access and cannot author assignments."
        )
    if membership.role != CourseRole.FACULTY:
        raise PermissionDeniedError(
            "Only faculty assigned to this course can create assignments."
        )

    cleaned_title = title.strip()
    cleaned_instructions = instructions.strip() if instructions else ""
    cleaned_status = status.strip() if status else AssignmentStatus.DRAFT

    # Scheduled assignment check: if release time is already in past, publish immediately
    if cleaned_status == AssignmentStatus.SCHEDULED and release_at and release_at <= timezone.now():
        cleaned_status = AssignmentStatus.PUBLISHED

    # Points conversion
    parsed_points = Decimal(str(points_possible)) if points_possible is not None else None

    try:
        validate_assignment_details(
            title=cleaned_title,
            submission_type=submission_type,
            status=cleaned_status,
            points_possible=parsed_points,
            instructions=cleaned_instructions,
            due_at=due_at,
            release_at=release_at,
        )
    except LMSRuleError as exc:
        raise ConflictError(str(exc), code="lms_validation_failed") from exc

    f_name = file_name.strip()
    f_size = file_size
    if file and hasattr(file, "name"):
        if not f_name:
            f_name = file.name
        if f_size is None and hasattr(file, "size"):
            f_size = file.size

    return CourseAssignment.objects.create(
        course=membership.course,
        title=cleaned_title,
        instructions=cleaned_instructions,
        submission_type=submission_type,
        points_possible=parsed_points or Decimal("100.00"),
        status=cleaned_status,
        due_at=due_at,
        release_at=release_at,
        file=file,
        file_name=f_name,
        file_size=f_size,
        created_by_user_id=actor.user_id,
    )


@transaction.atomic
def update_course_assignment(
    *,
    actor,
    course_code: str,
    assignment_id: int,
    title: str | None = None,
    instructions: str | None = None,
    submission_type: str | None = None,
    points_possible: Decimal | float | int | str | None = None,
    status: str | None = None,
    due_at: datetime | None = None,
    release_at: datetime | None = None,
    file: Any = None,
    file_name: str | None = None,
    file_size: int | None = None,
) -> CourseAssignment:
    """Update an existing assignment under CFR-LMS-006, AFR-LMS-006.3, and UC-LMS-007."""
    require(actor, P_MANAGE_ASSIGNMENT)

    membership = (
        CourseMembership.objects.filter(course__code=course_code, user_id=actor.user_id)
        .select_related("course")
        .first()
    )
    if membership is None:
        raise NotFoundError("Course not found or you are not linked to it.")

    if membership.role == CourseRole.TA:
        raise PermissionDeniedError(
            "Teaching Assistants are not permitted to author assignments."
        )
    if membership.role == CourseRole.STUDENT:
        raise PermissionDeniedError("Students cannot edit course assignments.")
    if membership.role == CourseRole.OBSERVER:
        raise PermissionDeniedError(
            "Observers have read-only access and cannot edit assignments."
        )
    if membership.role != CourseRole.FACULTY:
        raise PermissionDeniedError(
            "Only faculty assigned to this course can edit assignments."
        )

    assignment = (
        CourseAssignment.objects.filter(id=assignment_id, course=membership.course)
        .select_for_update()
        .first()
    )
    if assignment is None:
        raise NotFoundError("Course assignment not found.")

    new_title = assignment.title if title is None else title.strip()
    new_instructions = assignment.instructions if instructions is None else instructions.strip()
    new_submission_type = assignment.submission_type if submission_type is None else submission_type
    new_status = assignment.status if status is None else status.strip()
    new_due_at = assignment.due_at if due_at is None else due_at
    new_release_at = assignment.release_at if release_at is None else release_at

    if points_possible is not None:
        new_points = Decimal(str(points_possible))
    else:
        new_points = assignment.points_possible

    if (
        new_status == AssignmentStatus.SCHEDULED
        and new_release_at
        and new_release_at <= timezone.now()
    ):
        new_status = AssignmentStatus.PUBLISHED

    try:
        validate_assignment_details(
            title=new_title,
            submission_type=new_submission_type,
            status=new_status,
            points_possible=new_points,
            instructions=new_instructions,
            due_at=new_due_at,
            release_at=new_release_at,
        )
    except LMSRuleError as exc:
        raise ConflictError(str(exc), code="lms_validation_failed") from exc

    assignment.title = new_title
    assignment.instructions = new_instructions
    assignment.submission_type = new_submission_type
    assignment.points_possible = new_points
    assignment.status = new_status
    assignment.due_at = new_due_at
    assignment.release_at = new_release_at

    if file is not None:
        assignment.file = file
        assignment.file_name = file_name.strip() if file_name else getattr(file, "name", "")
        assignment.file_size = (
            file_size if file_size is not None else getattr(file, "size", None)
        )
    elif file_name is not None:
        assignment.file_name = file_name.strip()

    assignment.save()
    return assignment


@transaction.atomic
def delete_course_assignment(*, actor, course_code: str, assignment_id: int) -> None:
    """Delete an assignment item (Faculty only)."""
    require(actor, P_MANAGE_ASSIGNMENT)

    membership = (
        CourseMembership.objects.filter(course__code=course_code, user_id=actor.user_id)
        .select_related("course")
        .first()
    )
    if membership is None:
        raise NotFoundError("Course not found or you are not linked to it.")

    if membership.role != CourseRole.FACULTY:
        raise PermissionDeniedError(
            "Only faculty assigned to this course can delete assignments."
        )

    assignment = CourseAssignment.objects.filter(
        id=assignment_id, course=membership.course
    ).first()
    if assignment is None:
        raise NotFoundError("Course assignment not found.")

    assignment.delete()


def release_scheduled_assignments() -> int:
    """Publish scheduled assignments whose release time has arrived.

    Implements UC-LMS-015 and AFR-LMS-007.3.
    """
    now = timezone.now()
    return CourseAssignment.objects.filter(
        status=AssignmentStatus.SCHEDULED,
        release_at__lte=now,
    ).update(status=AssignmentStatus.PUBLISHED)
