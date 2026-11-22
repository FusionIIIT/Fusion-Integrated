"""Ownership- and membership-scoped LMS deadline and extension reads."""
from __future__ import annotations

from typing import Any

from django.utils import timezone

from modules.directory import contracts as directory
from modules.lms.domain.entities import CourseRole, DeadlineWindowStatus
from modules.lms.models import (
    CourseAssignment,
    CourseAssignmentExtension,
    CourseMembership,
)


def calculate_deadline_info(
    assignment: CourseAssignment,
    student_user_id: int | None = None,
) -> dict[str, Any]:
    """Calculate deadline, window state, and effective due date for a student.

    Satisfies CFR-LMS-008, AFR-LMS-008.2, AFR-LMS-009.2, and BR-LMS-013.
    """
    now = timezone.now()
    ext: CourseAssignmentExtension | None = None
    if student_user_id is not None:
        ext = assignment.extensions.filter(user_id=student_user_id).first()

    effective_due_at = ext.extended_due_at if ext else assignment.due_at
    is_extended = ext is not None
    extension_id = ext.id if ext else None
    extension_reason = ext.reason if ext else ""
    extended_due_iso = ext.extended_due_at.isoformat() if ext else None

    # Determine submission window status
    if assignment.release_at and now < assignment.release_at:
        window_status = DeadlineWindowStatus.NOT_OPEN
        is_submission_allowed = False
    elif effective_due_at is None or now <= effective_due_at:
        window_status = DeadlineWindowStatus.OPEN
        is_submission_allowed = True
    elif (
        (assignment.closes_at and now <= assignment.closes_at)
        or (assignment.allow_late and (not assignment.closes_at or now <= assignment.closes_at))
    ):
        window_status = DeadlineWindowStatus.LATE_ALLOWED
        is_submission_allowed = True
    else:
        window_status = DeadlineWindowStatus.CLOSED
        is_submission_allowed = False

    return {
        "assignment_id": assignment.id,
        "course_code": assignment.course.code,
        "title": assignment.title,
        "original_due_at": assignment.due_at.isoformat() if assignment.due_at else None,
        "closes_at": assignment.closes_at.isoformat() if assignment.closes_at else None,
        "allow_late": assignment.allow_late,
        "effective_due_at": effective_due_at.isoformat() if effective_due_at else None,
        "is_extended": is_extended,
        "extension_id": extension_id,
        "extended_due_at": extended_due_iso,
        "extension_reason": extension_reason,
        "window_status": window_status,
        "is_submission_allowed": is_submission_allowed,
    }


def get_assignment_deadline_info(
    *,
    principal,
    course_code: str,
    assignment_id: int,
) -> dict[str, Any] | None:
    """Retrieve deadline details for caller's role, preserving student extension privacy."""
    if principal is None:
        return None

    membership = (
        CourseMembership.objects.filter(course__code=course_code, user_id=principal.user_id)
        .select_related("course")
        .first()
    )
    if membership is None:
        return None

    assignment = (
        CourseAssignment.objects.filter(id=assignment_id, course=membership.course)
        .select_related("course")
        .first()
    )
    if assignment is None:
        return None

    # For students, compute personalized deadline with their own extension if any
    student_id = principal.user_id if membership.role == CourseRole.STUDENT else None
    info = calculate_deadline_info(assignment, student_user_id=student_id)
    info["role"] = membership.role
    info["can_manage_deadlines"] = bool(
        membership.role == CourseRole.FACULTY
        and principal.has_permission("lms.deadline.manage")
    )
    if membership.role in {CourseRole.FACULTY, CourseRole.TA}:
        info["total_extensions"] = assignment.extensions.count()
    else:
        info["total_extensions"] = 1 if info["is_extended"] else 0

    return info


def list_assignment_extensions(
    *,
    principal,
    course_code: str,
    assignment_id: int,
) -> list[dict[str, Any]] | None:
    """List all extensions for an assignment.

    Restricted strictly to Faculty and TAs (AFR-LMS-014.2).
    Students and Observers receive None to preserve student privacy (BR-LMS-014, AFR-LMS-015.3).
    """
    if principal is None:
        return None

    membership = (
        CourseMembership.objects.filter(course__code=course_code, user_id=principal.user_id)
        .select_related("course")
        .first()
    )
    if membership is None:
        return None

    if membership.role not in {CourseRole.FACULTY, CourseRole.TA}:
        return None

    assignment = CourseAssignment.objects.filter(
        id=assignment_id, course=membership.course
    ).first()
    if assignment is None:
        return None

    extensions = list(assignment.extensions.all().order_by("-created_at"))
    user_ids = {ext.user_id for ext in extensions} | {ext.granted_by_user_id for ext in extensions}
    user_facts = directory.get_users(list(user_ids)) if user_ids else {}

    results = []
    for ext in extensions:
        student_info = user_facts.get(ext.user_id)
        grantor_info = user_facts.get(ext.granted_by_user_id)
        grantor_name = (
            grantor_info.display_name if grantor_info else f"User {ext.granted_by_user_id}"
        )
        results.append({
            "id": ext.id,
            "assignment_id": assignment.id,
            "user_id": ext.user_id,
            "student_name": student_info.display_name if student_info else f"User {ext.user_id}",
            "student_email": student_info.email if student_info else "",
            "extended_due_at": ext.extended_due_at.isoformat(),
            "reason": ext.reason,
            "granted_by_user_id": ext.granted_by_user_id,
            "granted_by_name": grantor_name,
            "created_at": ext.created_at.isoformat(),
            "updated_at": ext.updated_at.isoformat(),
        })

    return results
