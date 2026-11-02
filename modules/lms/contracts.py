"""Cross-module contracts for LMS (Course Management) (ADR-0013).

Other modules can only import from here, never from LMS models or services directly.
"""
from dataclasses import dataclass
from typing import Sequence

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


def get_user_enrolled_courses(user_id: int) -> list[CourseSummaryDTO]:
    """Return active courses a user is enrolled in or assigned to."""
    memberships = (
        CourseMembership.objects.filter(user_id=user_id, course__is_active=True)
        .select_related("course")
        .order_by("course__course_code")
    )
    return [
        CourseSummaryDTO(
            course_id=m.course.id,
            course_code=m.course.course_code,
            title=m.course.title,
            instructor_user_id=m.course.instructor_user_id,
            is_active=m.course.is_active,
        )
        for m in memberships
    ]


def is_user_in_course(course_id: int, user_id: int) -> bool:
    """Return True if user has an active membership in the given course."""
    return CourseMembership.objects.filter(course_id=course_id, user_id=user_id).exists()
