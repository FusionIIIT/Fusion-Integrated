"""Cross-module contracts for LMS (Course Management) (ADR-0013).

Other modules can only import from here, never from LMS models or services directly.
Plural by signature.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from .models import CourseMembership, CourseWorkspace


@dataclass(frozen=True)
class CourseSummaryDTO:
    course_id: int
    course_code: str
    title: str
    instructor_user_id: int
    is_active: bool


@dataclass(frozen=True)
class CourseEnrollmentDTO:
    course_id: int
    user_id: int
    role: str
    can_post_announcements: bool


def get_courses(course_ids: Sequence[int]) -> dict[int, CourseSummaryDTO]:
    """Return course metadata for the given course IDs."""
    ids = {int(i) for i in course_ids if i is not None}
    if not ids:
        return {}
    courses = CourseWorkspace.objects.filter(id__in=ids)
    return {
        c.id: CourseSummaryDTO(
            course_id=c.id,
            course_code=c.course_code,
            title=c.title,
            instructor_user_id=c.instructor_user_id,
            is_active=c.is_active,
        )
        for c in courses
    }


def get_student_enrollments(student_ids: Sequence[int]) -> dict[int, list[CourseEnrollmentDTO]]:
    """Return active course enrollments for the given student user IDs."""
    ids = {int(i) for i in student_ids if i is not None}
    if not ids:
        return {}
    memberships = (
        CourseMembership.objects.filter(user_id__in=ids, course__is_active=True)
        .select_related("course")
        .order_by("course__course_code")
    )
    result: dict[int, list[CourseEnrollmentDTO]] = {uid: [] for uid in ids}
    for m in memberships:
        result[m.user_id].append(
            CourseEnrollmentDTO(
                course_id=m.course_id,
                user_id=m.user_id,
                role=m.role,
                can_post_announcements=m.can_post_announcements,
            )
        )
    return result


def get_instructor_courses(instructor_ids: Sequence[int]) -> dict[int, list[CourseSummaryDTO]]:
    """Return courses instructed by the given instructor user IDs."""
    ids = {int(i) for i in instructor_ids if i is not None}
    if not ids:
        return {}
    courses = CourseWorkspace.objects.filter(instructor_user_id__in=ids, is_active=True).order_by(
        "course_code"
    )
    result: dict[int, list[CourseSummaryDTO]] = {uid: [] for uid in ids}
    for c in courses:
        result[c.instructor_user_id].append(
            CourseSummaryDTO(
                course_id=c.id,
                course_code=c.course_code,
                title=c.title,
                instructor_user_id=c.instructor_user_id,
                is_active=c.is_active,
            )
        )
    return result


def is_user_in_course(course_id: int, user_id: int) -> bool:
    """Return True if user has an active membership in the given course."""
    return CourseMembership.objects.filter(course_id=course_id, user_id=user_id).exists()
