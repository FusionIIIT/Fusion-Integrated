"""Course workspace service operations."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied
from django.db import transaction

from modules.lms.domain.constants import CourseRole
from modules.lms.models import CourseMembership, CourseWorkspace
from modules.lms.selectors.scoping import is_course_instructor


def update_course_details(
    course_id: int,
    syllabus: str,
    schedule_info: str,
    principal: Any,
) -> CourseWorkspace:
    """Updates syllabus and schedule info for an assigned course workspace (CFR-LMS-002)."""
    if not is_course_instructor(course_id, principal):
        raise PermissionDenied("Only assigned instructors may update course details.")

    workspace, _ = CourseWorkspace.objects.get_or_create(
        course_id=course_id,
        defaults={"course_code": f"C-{course_id}", "title": f"Course {course_id}"},
    )
    workspace.syllabus = syllabus
    workspace.schedule_info = schedule_info
    workspace.save(update_fields=["syllabus", "schedule_info", "updated_at"])
    return workspace


def configure_membership(
    course_id: int,
    user_id: int,
    role: str,
    can_post_announcement: bool = False,
    can_grade: bool = True,
) -> CourseMembership:
    """Provisions or updates a course membership entry."""
    with transaction.atomic():
        membership, _ = CourseMembership.objects.update_or_create(
            course_id=course_id,
            user_id=user_id,
            role=role,
            defaults={
                "can_post_announcement": can_post_announcement if role == CourseRole.TA else False,
                "can_grade": can_grade if role == CourseRole.TA else False,
            },
        )
    return membership
