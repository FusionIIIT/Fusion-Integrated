"""Ownership- and membership-scoped LMS course reads."""
from __future__ import annotations

from typing import Any

from modules.directory import contracts as directory
from modules.lms.domain.entities import CourseRole
from modules.lms.models import CourseMembership


def visible_courses(principal) -> list[dict[str, Any]]:
    """List courses that the principal is enrolled in, assigned to, or linked to."""
    if principal is None:
        return []

    memberships = (
        CourseMembership.objects.filter(user_id=principal.user_id)
        .select_related("course")
        .order_by("course__code")
    )

    out = []
    for m in memberships:
        c = m.course
        out.append({
            "code": c.code,
            "title": c.title,
            "description": c.description,
            "schedule": c.schedule,
            "status": c.status,
            "role": m.role,
        })
    return out


def course_workspace_details(*, principal, course_code: str) -> dict[str, Any] | None:
    """Retrieve full course home information if principal is authorized for this course.

    Returns None if course does not exist or caller is not enrolled/assigned/linked,
    strictly satisfying AFR-LMS-001.3 and BR-LMS-001.
    """
    if principal is None:
        return None

    caller_membership = (
        CourseMembership.objects.filter(course__code=course_code, user_id=principal.user_id)
        .select_related("course")
        .first()
    )
    if caller_membership is None:
        return None

    course = caller_membership.course
    all_members = list(
        CourseMembership.objects.filter(course=course)
        .filter(role__in=[CourseRole.FACULTY, CourseRole.TA])
        .values_list("user_id", "role")
    )

    instructor_uids = [uid for uid, r in all_members if r == CourseRole.FACULTY]
    ta_uids = [uid for uid, r in all_members if r == CourseRole.TA]

    # Resolve names & emails via directory contract without cross-module joins
    user_facts = directory.get_users(instructor_uids + ta_uids)

    def _format_user(uid: int) -> dict[str, Any]:
        info = user_facts.get(uid)
        return {
            "user_id": uid,
            "display_name": info.display_name if info else f"User {uid}",
            "email": info.email if info else "",
            "department": info.department if info else "",
        }

    can_edit = bool(
        caller_membership.role == CourseRole.FACULTY
        and principal.has_permission("lms.course.manage")
    )

    return {
        "code": course.code,
        "title": course.title,
        "description": course.description,
        "syllabus": course.syllabus,
        "schedule": course.schedule,
        "status": course.status,
        "role": caller_membership.role,
        "can_edit": can_edit,
        "instructors": [_format_user(uid) for uid in instructor_uids],
        "teaching_assistants": [_format_user(uid) for uid in ta_uids],
    }
