"""Transactional Course Announcements writes."""
from __future__ import annotations

from django.db import transaction

from core.api.exceptions import NotFoundError, PermissionDeniedError
from modules.lms.domain.entities import CourseRole, validate_announcement_details
from modules.lms.models import CourseAnnouncement, CourseMembership
from modules.lms.services.authz import require

P_MANAGE_ANNOUNCEMENT = "lms.announcement.manage"


@transaction.atomic
def post_course_announcement(
    *,
    actor,
    course_code: str,
    title: str,
    content: str,
) -> CourseAnnouncement:
    """Post a course-wide announcement under CFR-LMS-005 and UC-LMS-005.

    Strictly restricted to Faculty assigned to this course (AFR-LMS-005.1, BR-LMS-007).
    TAs, Students, and Observers are prevented from unauthorized posting
    (AFR-LMS-005.2, AFR-LMS-014.2, AFR-LMS-015.4, BR-LMS-007).
    """
    require(actor, P_MANAGE_ANNOUNCEMENT)

    membership = (
        CourseMembership.objects.filter(course__code=course_code, user_id=actor.user_id)
        .select_related("course")
        .first()
    )
    if membership is None:
        raise NotFoundError("Course not found or you are not linked to it.")

    if membership.role == CourseRole.OBSERVER:
        raise PermissionDeniedError(
            "Observers have read-only access and cannot post announcements."
        )
    if membership.role == CourseRole.STUDENT:
        raise PermissionDeniedError("Students cannot post course announcements.")
    if membership.role == CourseRole.TA:
        # BR-LMS-007 specifies: "Faculty may post course announcements; a TA may post only
        # where permitted by Faculty for that course.
        # Exceptions / Exclusions: Mechanism/configurability unresolved."
        # In accordance with strict instructions not to invent unconfigured flags,
        # TAs are denied announcement posting by default.
        raise PermissionDeniedError(
            "Teaching Assistants are not permitted to post announcements for this course."
        )

    if membership.role != CourseRole.FACULTY:
        raise PermissionDeniedError(
            "Only faculty assigned to this course can post announcements."
        )

    validate_announcement_details(title=title, content=content)

    return CourseAnnouncement.objects.create(
        course=membership.course,
        title=title.strip(),
        content=content.strip(),
        created_by_user_id=actor.user_id,
        author_role=membership.role,
    )
