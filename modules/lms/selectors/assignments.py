"""Ownership- and membership-scoped LMS course assignment reads."""
from __future__ import annotations

from typing import Any

from django.db.models import Q
from django.utils import timezone

from core.api.exceptions import NotFoundError
from modules.lms.domain.entities import AssignmentStatus, CourseRole
from modules.lms.models import CourseAssignment, CourseMembership


def _assignment_to_dict(a: CourseAssignment) -> dict[str, Any]:
    return {
        "id": a.id,
        "course_code": a.course.code,
        "title": a.title,
        "instructions": a.instructions,
        "submission_type": a.submission_type,
        "points_possible": float(a.points_possible),
        "status": a.status,
        "due_at": a.due_at.isoformat() if a.due_at else None,
        "release_at": a.release_at.isoformat() if a.release_at else None,
        "file_name": a.file_name or (a.file.name if a.file else ""),
        "file_size": a.file_size,
        "has_file": bool(a.file),
        "created_by_user_id": a.created_by_user_id,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }


def list_course_assignments(*, principal, course_code: str) -> dict[str, Any] | None:
    """List course assignments according to CFR-LMS-006, CFR-LMS-007, and BR-LMS-011.

    Faculty sees all assignments (draft, scheduled, published) with management capabilities.
    Students, TAs, and Observers strictly see published or released assignments only;
    drafts and future-scheduled assignments are never exposed (AFR-LMS-007.2, BR-LMS-011).
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

    course = membership.course
    now = timezone.now()
    qs = CourseAssignment.objects.filter(course=course).select_related("course")

    if membership.role != CourseRole.FACULTY:
        # Students, TAs, Observers: Only published or released scheduled assignments
        qs = qs.filter(
            Q(status=AssignmentStatus.PUBLISHED)
            | Q(status=AssignmentStatus.SCHEDULED, release_at__lte=now)
        )

    assignments = list(qs.order_by("due_at", "-created_at"))
    can_manage = bool(
        membership.role == CourseRole.FACULTY
        and principal.has_permission("lms.assignment.manage")
    )

    items = [_assignment_to_dict(a) for a in assignments]
    return {
        "course_code": course.code,
        "course_title": course.title,
        "role": membership.role,
        "can_manage": can_manage,
        "assignments": items,
        "total_count": len(items),
    }


def get_course_assignment_detail(
    *,
    principal,
    course_code: str,
    assignment_id: int,
) -> dict[str, Any] | None:
    """Retrieve detailed information for a single assignment if authorized."""
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

    if membership.role != CourseRole.FACULTY:
        now = timezone.now()
        is_released = (
            assignment.status == AssignmentStatus.PUBLISHED
            or (
                assignment.status == AssignmentStatus.SCHEDULED
                and assignment.release_at
                and assignment.release_at <= now
            )
        )
        if not is_released:
            return None

    return _assignment_to_dict(assignment)


def get_assignment_for_download(
    *,
    principal,
    course_code: str,
    assignment_id: int,
) -> tuple[CourseAssignment, str]:
    """Retrieve assignment file for download (CFR-LMS-007, AFR-LMS-007.4, UC-LMS-009)."""
    if principal is None:
        raise NotFoundError("Course assignment not found.")

    membership = (
        CourseMembership.objects.filter(course__code=course_code, user_id=principal.user_id)
        .select_related("course")
        .first()
    )
    if membership is None:
        raise NotFoundError("Course not found or you are not linked to it.")

    assignment = (
        CourseAssignment.objects.filter(id=assignment_id, course=membership.course)
        .select_related("course")
        .first()
    )
    if assignment is None or not assignment.file:
        raise NotFoundError("Assignment file not found.")

    if membership.role != CourseRole.FACULTY:
        now = timezone.now()
        is_released = (
            assignment.status == AssignmentStatus.PUBLISHED
            or (
                assignment.status == AssignmentStatus.SCHEDULED
                and assignment.release_at
                and assignment.release_at <= now
            )
        )
        if not is_released:
            raise NotFoundError("Assignment content is not released yet.")

    return assignment, assignment.file.path
