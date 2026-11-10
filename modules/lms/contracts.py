"""LMS public contract surface.

The ONLY thing other modules may import from modules.lms.
Every cross-module getter takes a Sequence, never a singular id (contracts_are_plural).
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from modules.lms.domain.entities import AssignmentStatus, MaterialStatus
from modules.lms.models import (
    Course,
    CourseAnnouncement,
    CourseAssignment,
    CourseMaterial,
    CourseMembership,
)


@dataclass(frozen=True)
class CourseDTO:
    code: str
    title: str
    description: str
    status: str


def get_courses(course_codes: Sequence[str]) -> dict[str, CourseDTO]:
    """Retrieve course basic details, batched by course codes."""
    codes = {str(c).strip() for c in course_codes if c}
    if not codes:
        return {}
    courses = Course.objects.filter(code__in=codes)
    return {
        c.code: CourseDTO(
            code=c.code,
            title=c.title,
            description=c.description,
            status=c.status,
        )
        for c in courses
    }


def get_user_course_codes(user_ids: Sequence[int]) -> dict[int, list[str]]:
    """Retrieve active course codes per user, batched by user IDs."""
    ids = {int(uid) for uid in user_ids if uid is not None}
    if not ids:
        return {}
    memberships = (
        CourseMembership.objects.filter(user_id__in=ids)
        .values_list("user_id", "course__code")
    )
    result: dict[int, list[str]] = {uid: [] for uid in ids}
    for uid, code in memberships:
        result.setdefault(uid, []).append(code)
    return result


def get_course_materials(
    course_codes: Sequence[str],
) -> dict[str, list[dict[str, Any]]]:
    """Retrieve published course materials, batched by course codes (contracts_are_plural)."""
    codes = {str(c).strip() for c in course_codes if c}
    if not codes:
        return {}
    materials = (
        CourseMaterial.objects.filter(course__code__in=codes, status=MaterialStatus.PUBLISHED)
        .select_related("course")
        .order_by("course__code", "section_title", "order")
    )
    result: dict[str, list[dict[str, Any]]] = {code: [] for code in codes}
    for m in materials:
        result.setdefault(m.course.code, []).append({
            "id": m.id,
            "title": m.title,
            "material_type": m.material_type,
            "section_title": m.section_title,
            "file_name": m.file_name,
            "link_url": m.link_url,
        })
    return result


def get_course_announcements(
    course_codes: Sequence[str],
) -> dict[str, list[dict[str, Any]]]:
    """Retrieve course announcements, batched by course codes (contracts_are_plural)."""
    codes = {str(c).strip() for c in course_codes if c}
    if not codes:
        return {}
    announcements = (
        CourseAnnouncement.objects.filter(course__code__in=codes)
        .select_related("course")
        .order_by("course__code", "-created_at")
    )
    result: dict[str, list[dict[str, Any]]] = {code: [] for code in codes}
    for a in announcements:
        result.setdefault(a.course.code, []).append({
            "id": a.id,
            "title": a.title,
            "content": a.content,
            "created_by_user_id": a.created_by_user_id,
            "author_role": a.author_role,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        })
    return result


def get_course_assignments(
    course_codes: Sequence[str],
) -> dict[str, list[dict[str, Any]]]:
    """Retrieve published course assignments, batched by course codes (contracts_are_plural)."""
    codes = {str(c).strip() for c in course_codes if c}
    if not codes:
        return {}
    assignments = (
        CourseAssignment.objects.filter(course__code__in=codes, status=AssignmentStatus.PUBLISHED)
        .select_related("course")
        .order_by("course__code", "due_at", "-created_at")
    )
    result: dict[str, list[dict[str, Any]]] = {code: [] for code in codes}
    for a in assignments:
        result.setdefault(a.course.code, []).append({
            "id": a.id,
            "title": a.title,
            "instructions": a.instructions,
            "submission_type": a.submission_type,
            "points_possible": float(a.points_possible),
            "status": a.status,
            "due_at": a.due_at.isoformat() if a.due_at else None,
            "release_at": a.release_at.isoformat() if a.release_at else None,
            "closes_at": a.closes_at.isoformat() if a.closes_at else None,
            "allow_late": a.allow_late,
            "file_name": a.file_name,
        })
    return result


def get_assignment_deadlines(
    assignment_ids: Sequence[int],
    student_user_id: int | None = None,
) -> dict[int, dict[str, Any]]:
    """Retrieve deadline and window status for assignments (contracts_are_plural)."""
    ids = {int(aid) for aid in assignment_ids if aid is not None}
    if not ids:
        return {}
    assignments = (
        CourseAssignment.objects.filter(id__in=ids)
        .prefetch_related("extensions")
    )
    from modules.lms.selectors.deadlines import calculate_deadline_info

    return {
        a.id: calculate_deadline_info(a, student_user_id=student_user_id)
        for a in assignments
    }
