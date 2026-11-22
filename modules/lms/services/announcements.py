"""Course announcement service operations."""

from __future__ import annotations

from typing import Any

from django.db import transaction

from core.api.exceptions import BadRequestError, NotFoundError, PermissionDeniedError
from modules.lms.domain.constants import CourseRole
from modules.lms.models import CourseAnnouncement
from modules.lms.selectors.scoping import get_course_membership, is_course_instructor


def post_announcement(
    course_id: int,
    title: str,
    content: str,
    principal: Any,
) -> CourseAnnouncement:
    """Posts a course announcement (BR-LMS-007)."""
    user_id = getattr(principal, "user_id", None) or getattr(principal, "erp_user_id", None) or 0
    if not (title and title.strip()):
        raise BadRequestError("Announcement title cannot be empty.")
    if not (content and content.strip()):
        raise BadRequestError("Announcement content cannot be empty.")

    if is_course_instructor(course_id, principal):
        role_label = CourseRole.INSTRUCTOR
    else:
        membership = get_course_membership(course_id, user_id)
        if (
            not membership
            or membership.role != CourseRole.TA
            or not membership.can_post_announcement
        ):
            raise PermissionDeniedError(
                "You do not have permission to post announcements in this course."
            )
        role_label = CourseRole.TA

    with transaction.atomic():
        return CourseAnnouncement.objects.create(
            course_id=course_id,
            title=title,
            content=content,
            author_id=user_id,
            author_role=role_label,
        )


def delete_announcement(announcement_id: int, principal: Any) -> None:
    """Deletes an announcement if caller is an instructor for the course."""
    with transaction.atomic():
        announcement = (
            CourseAnnouncement.objects.select_for_update().filter(id=announcement_id).first()
        )
        if not announcement:
            raise NotFoundError("Course announcement not found.")
        if not is_course_instructor(announcement.course_id, principal):
            raise PermissionDeniedError("Only assigned instructors may delete announcements.")
        announcement.delete()
