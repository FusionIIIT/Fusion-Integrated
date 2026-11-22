"""Ownership- and membership-scoped LMS course announcement reads."""
from __future__ import annotations

from typing import Any

from modules.directory import contracts as directory
from modules.lms.domain.entities import CourseRole
from modules.lms.models import CourseAnnouncement, CourseMembership


def list_course_announcements(
    *,
    principal,
    course_code: str,
) -> dict[str, Any] | None:
    """List course announcements if principal is authorized for this course.

    Visible to all users enrolled in or linked to the course (Faculty, TA, Student, Observer)
    strictly satisfying CFR-LMS-005, AFR-LMS-005.4, AFR-LMS-014.1, AFR-LMS-015.1, and BR-LMS-008.
    Returns None if course does not exist or caller is not authorized (BR-LMS-001).
    """
    if principal is None:
        return None

    membership = (
        CourseMembership.objects.filter(course__code=course_code, user_id=principal.user_id)
        .select_related("course")
        .first()
    )
    if membership is None:
        return None

    course = membership.course
    role = membership.role

    # Faculty can post; TAs are not permitted unless authorized (unresolved spec policy).
    can_post = bool(
        role == CourseRole.FACULTY and principal.has_permission("lms.announcement.manage")
    )

    announcements = list(course.announcements.all().order_by("-created_at"))
    author_ids = list({a.created_by_user_id for a in announcements})
    user_facts = directory.get_users(author_ids) if author_ids else {}

    items = []
    for a in announcements:
        author_info = user_facts.get(a.created_by_user_id)
        author_name = (
            author_info.display_name if author_info else f"User {a.created_by_user_id}"
        )
        items.append({
            "id": a.id,
            "course_code": course.code,
            "title": a.title,
            "content": a.content,
            "created_by_user_id": a.created_by_user_id,
            "author_name": author_name,
            "author_role": a.author_role,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "updated_at": a.updated_at.isoformat() if a.updated_at else None,
        })

    return {
        "course_code": course.code,
        "course_title": course.title,
        "role": role,
        "can_post": can_post,
        "announcements": items,
        "total_count": len(items),
    }


def get_course_announcement_detail(
    *,
    principal,
    course_code: str,
    announcement_id: int,
) -> dict[str, Any] | None:
    """Retrieve details for a single course announcement.

    Returns None if the caller is not a member of the course or the announcement does not exist.
    """
    if principal is None:
        return None

    membership = (
        CourseMembership.objects.filter(course__code=course_code, user_id=principal.user_id)
        .select_related("course")
        .first()
    )
    if membership is None:
        return None

    course = membership.course
    announcement = CourseAnnouncement.objects.filter(
        course=course, id=announcement_id
    ).first()
    if announcement is None:
        return None

    author_facts = directory.get_users([announcement.created_by_user_id])
    author_info = author_facts.get(announcement.created_by_user_id)
    author_name = (
        author_info.display_name
        if author_info
        else f"User {announcement.created_by_user_id}"
    )

    return {
        "id": announcement.id,
        "course_code": course.code,
        "title": announcement.title,
        "content": announcement.content,
        "created_by_user_id": announcement.created_by_user_id,
        "author_name": author_name,
        "author_role": announcement.author_role,
        "created_at": announcement.created_at.isoformat() if announcement.created_at else None,
        "updated_at": announcement.updated_at.isoformat() if announcement.updated_at else None,
    }
