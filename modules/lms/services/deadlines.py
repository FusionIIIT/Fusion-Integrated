"""Transactional LMS Deadline and Extension writes."""
from __future__ import annotations

from datetime import datetime

from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.lms.domain.entities import (
    CourseRole,
    validate_deadline_window,
    validate_extension_details,
)
from modules.lms.domain.errors import LMSRuleError
from modules.lms.models import (
    CourseAssignment,
    CourseAssignmentExtension,
    CourseMembership,
)
from modules.lms.services.authz import require

P_MANAGE_DEADLINE = "lms.deadline.manage"


@transaction.atomic
def update_assignment_window(
    *,
    actor,
    course_code: str,
    assignment_id: int,
    due_at: datetime | None = None,
    closes_at: datetime | None = None,
    allow_late: bool | None = None,
) -> CourseAssignment:
    """Configure submission deadline and window controls (CFR-LMS-006, BR-LMS-009).

    Restricted strictly to Faculty assigned to this course (AFR-LMS-006.1, BR-LMS-004).
    TAs, Students, and Observers cannot modify deadline parameters (AFR-LMS-014.3, AFR-LMS-015.4).
    """
    require(actor, P_MANAGE_DEADLINE)

    membership = (
        CourseMembership.objects.filter(course__code=course_code, user_id=actor.user_id)
        .select_related("course")
        .first()
    )
    if membership is None:
        raise NotFoundError("Course not found or you are not linked to it.")

    if membership.role == CourseRole.TA:
        raise PermissionDeniedError(
            "Teaching Assistants are not permitted to configure assignment deadlines."
        )
    if membership.role != CourseRole.FACULTY:
        raise PermissionDeniedError(
            "Only faculty assigned to this course can configure deadlines."
        )

    assignment = (
        CourseAssignment.objects.filter(id=assignment_id, course=membership.course)
        .select_for_update()
        .first()
    )
    if assignment is None:
        raise NotFoundError("Course assignment not found.")

    new_due_at = assignment.due_at if due_at is None else due_at
    new_closes_at = assignment.closes_at if closes_at is None else closes_at
    new_allow_late = assignment.allow_late if allow_late is None else allow_late

    try:
        validate_deadline_window(
            due_at=new_due_at,
            closes_at=new_closes_at,
            release_at=assignment.release_at,
        )
    except LMSRuleError as exc:
        raise ConflictError(str(exc), code="deadline_window_invalid") from exc

    assignment.due_at = new_due_at
    assignment.closes_at = new_closes_at
    assignment.allow_late = new_allow_late
    assignment.save()

    return assignment


@transaction.atomic
def grant_assignment_extension(
    *,
    actor,
    course_code: str,
    assignment_id: int,
    student_user_id: int,
    extended_due_at: datetime,
    reason: str = "",
) -> CourseAssignmentExtension:
    """Grant or update an individual student deadline extension.

    Only Faculty assigned to this course can grant extensions (BR-LMS-004).
    Enforces student-specific scope, preserves original assignment deadline,
    and maintains student privacy (CFR-LMS-008, AFR-LMS-009.2, BR-LMS-014).
    """
    require(actor, P_MANAGE_DEADLINE)

    membership = (
        CourseMembership.objects.filter(course__code=course_code, user_id=actor.user_id)
        .select_related("course")
        .first()
    )
    if membership is None:
        raise NotFoundError("Course not found or you are not linked to it.")

    if membership.role == CourseRole.TA:
        raise PermissionDeniedError(
            "Teaching Assistants are not permitted to grant deadline extensions."
        )
    if membership.role != CourseRole.FACULTY:
        raise PermissionDeniedError(
            "Only faculty assigned to this course can grant deadline extensions."
        )

    assignment = CourseAssignment.objects.filter(
        id=assignment_id, course=membership.course
    ).first()
    if assignment is None:
        raise NotFoundError("Course assignment not found.")

    # Confirm student is registered in this course
    student_membership = CourseMembership.objects.filter(
        course=membership.course,
        user_id=student_user_id,
        role=CourseRole.STUDENT,
    ).first()
    if student_membership is None:
        raise ConflictError(
            f"User {student_user_id} is not an enrolled student in course {course_code}."
        )

    try:
        validate_extension_details(
            original_due_at=assignment.due_at,
            extended_due_at=extended_due_at,
            student_user_id=student_user_id,
        )
    except LMSRuleError as exc:
        raise ConflictError(str(exc), code="extension_validation_failed") from exc

    extension, _ = CourseAssignmentExtension.objects.update_or_create(
        assignment=assignment,
        user_id=student_user_id,
        defaults={
            "extended_due_at": extended_due_at,
            "reason": reason.strip() if reason else "",
            "granted_by_user_id": actor.user_id,
        },
    )
    return extension


@transaction.atomic
def revoke_assignment_extension(
    *,
    actor,
    course_code: str,
    assignment_id: int,
    extension_id: int,
) -> None:
    """Revoke an approved student deadline extension (Faculty only)."""
    require(actor, P_MANAGE_DEADLINE)

    membership = (
        CourseMembership.objects.filter(course__code=course_code, user_id=actor.user_id)
        .select_related("course")
        .first()
    )
    if membership is None:
        raise NotFoundError("Course not found or you are not linked to it.")

    if membership.role != CourseRole.FACULTY:
        raise PermissionDeniedError(
            "Only faculty assigned to this course can revoke deadline extensions."
        )

    extension = CourseAssignmentExtension.objects.filter(
        id=extension_id,
        assignment__id=assignment_id,
        assignment__course=membership.course,
    ).first()
    if extension is None:
        raise NotFoundError("Extension record not found.")

    extension.delete()
