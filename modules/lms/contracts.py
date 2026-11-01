"""LMS public contract surface.

The ONLY thing other modules may import from modules.lms.
Every cross-module getter takes a Sequence, never a singular id (contracts_are_plural).
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from modules.lms.models import Course, CourseMembership


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
