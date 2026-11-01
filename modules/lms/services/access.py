"""Course-level authorization and role checking (BR-LMS-001, BR-LMS-003, BR-LMS-004)."""
from __future__ import annotations

from typing import Optional
from rest_framework.exceptions import PermissionDenied, NotFound
from modules.lms.models import Course, CourseMembership


def get_course_membership(course_id: int, user_id: int) -> Optional[CourseMembership]:
    """Retrieve active course membership for user."""
    return CourseMembership.objects.filter(
        course_id=course_id, user_id=user_id, is_active=True
    ).first()


def require_course_access(course_id: int, user_id: int) -> tuple[Course, CourseMembership]:
    """Verify user is enrolled, assigned, or linked to the course (BR-LMS-001).

    Returns the course and membership. Raises NotFound / PermissionDenied if unlinked.
    """
    course = Course.objects.filter(id=course_id, is_active=True).first()
    if not course:
        raise NotFound("Course not found.")

    membership = get_course_membership(course_id, user_id)
    if not membership:
        raise PermissionDenied("You do not have access to this course workspace.")

    return course, membership


def check_faculty_or_ta(membership: CourseMembership) -> bool:
    return membership.role in ("faculty", "ta")


def require_faculty(membership: CourseMembership, error_msg="Only course faculty may perform this action."):
    if membership.role != "faculty":
        raise PermissionDenied(error_msg)


def require_can_announce(course: Course, membership: CourseMembership):
    """BR-LMS-007: Faculty may post announcements; TA may post only where permitted."""
    if membership.role == "faculty":
        return
    if membership.role == "ta" and course.allow_ta_announcements:
        return
    raise PermissionDenied("You do not have permission to post announcements in this course.")


def require_can_grade(course: Course, membership: CourseMembership):
    """BR-LMS-015, BR-LMS-004: Faculty or TA (if enabled) can grade submissions."""
    if membership.role == "faculty":
        return
    if membership.role == "ta" and course.allow_ta_grading:
        return
    raise PermissionDenied("You do not have grading permissions in this course.")


def require_non_observer(membership: CourseMembership, error_msg: str = "Observers have read-only access and cannot access student-specific data."):
    """BR-LMS-003: Observers cannot view student submissions, grades, or perform writes."""
    if membership.role == "observer":
        raise PermissionDenied(error_msg)
