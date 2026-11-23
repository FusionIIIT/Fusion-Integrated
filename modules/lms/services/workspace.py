"""Course workspace service operations."""

from __future__ import annotations

from typing import Any

from django.db import transaction

from core.api.exceptions import PermissionDeniedError
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
        raise PermissionDeniedError("Only assigned course instructors may update course details.")

    with transaction.atomic():
        workspace = CourseWorkspace.objects.select_for_update().filter(course_id=course_id).first()
        if not workspace:
            workspace = CourseWorkspace.objects.create(
                course_id=course_id,
                course_code=f"C-{course_id}",
                title=f"Course {course_id}",
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
        membership, _ = CourseMembership.objects.select_for_update().update_or_create(
            course_id=course_id,
            user_id=user_id,
            role=role,
            defaults={
                "can_post_announcement": can_post_announcement if role == CourseRole.TA else False,
                "can_grade": can_grade if role == CourseRole.TA else False,
            },
        )
    return membership
