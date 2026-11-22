"""LMS queryset scoping and principal authorization checks."""

from __future__ import annotations

from typing import Any

from django.db.models import QuerySet

from modules.lms.domain.constants import CourseRole, MembershipStatus
from modules.lms.models import CourseMembership, CourseWorkspace


def get_user_courses_queryset(principal: Any) -> QuerySet[CourseWorkspace]:
    """Returns workspaces for courses the principal is actively enrolled in,
    assigned to, or linked.
    """
    user_id = getattr(principal, "user_id", None) or getattr(principal, "erp_user_id", None)
    if user_id is None:
        return CourseWorkspace.objects.none()

    linked_course_ids = CourseMembership.objects.filter(
        user_id=user_id,
        status=MembershipStatus.ACTIVE,
    ).values_list("course_id", flat=True)

    return CourseWorkspace.objects.filter(course_id__in=linked_course_ids)


def get_course_membership(course_id: int, user_id: int) -> CourseMembership | None:
    return CourseMembership.objects.filter(
        course_id=course_id,
        user_id=user_id,
        status=MembershipStatus.ACTIVE,
    ).first()


def has_course_access(course_id: int, principal: Any) -> bool:
    user_id = getattr(principal, "user_id", None) or getattr(principal, "erp_user_id", None)
    if user_id is None:
        return False
    return CourseMembership.objects.filter(
        course_id=course_id,
        user_id=user_id,
        status=MembershipStatus.ACTIVE,
    ).exists()


def is_course_instructor(course_id: int, principal: Any) -> bool:
    user_id = getattr(principal, "user_id", None) or getattr(principal, "erp_user_id", None)
    if user_id is None:
        return False
    return CourseMembership.objects.filter(
        course_id=course_id,
        user_id=user_id,
        role=CourseRole.INSTRUCTOR,
        status=MembershipStatus.ACTIVE,
    ).exists()


def is_course_ta(course_id: int, principal: Any) -> bool:
    user_id = getattr(principal, "user_id", None) or getattr(principal, "erp_user_id", None)
    if user_id is None:
        return False
    return CourseMembership.objects.filter(
        course_id=course_id,
        user_id=user_id,
        role=CourseRole.TA,
        status=MembershipStatus.ACTIVE,
    ).exists()


def is_course_observer(course_id: int, principal: Any) -> bool:
    user_id = getattr(principal, "user_id", None) or getattr(principal, "erp_user_id", None)
    if user_id is None:
        return False
    return CourseMembership.objects.filter(
        course_id=course_id,
        user_id=user_id,
        role=CourseRole.OBSERVER,
        status=MembershipStatus.ACTIVE,
    ).exists()
