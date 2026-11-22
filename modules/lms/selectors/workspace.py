"""Course workspace selectors."""

from __future__ import annotations

from typing import Any

from modules.lms.domain.constants import CourseRole, MembershipStatus
from modules.lms.models import CourseMembership, CourseWorkspace
from modules.lms.selectors.scoping import has_course_access


def list_user_courses(principal: Any) -> list[dict[str, Any]]:
    user_id = getattr(principal, "user_id", None) or getattr(principal, "erp_user_id", None)
    if user_id is None:
        return []

    memberships = CourseMembership.objects.filter(
        user_id=user_id,
        status=MembershipStatus.ACTIVE,
    )
    course_ids = [m.course_id for m in memberships]
    roles_by_course = {m.course_id: m.role for m in memberships}

    workspaces = CourseWorkspace.objects.filter(course_id__in=course_ids)
    return [
        {
            "id": w.id,
            "course_id": w.course_id,
            "course_code": w.course_code,
            "title": w.title,
            "role": roles_by_course.get(w.course_id, "STUDENT"),
        }
        for w in workspaces
    ]


def get_course_home_details(course_id: int, principal: Any) -> dict[str, Any] | None:
    if not has_course_access(course_id, principal):
        return None

    workspace = CourseWorkspace.objects.filter(course_id=course_id).first()
    if not workspace:
        return None

    # Teaching staff roster: Instructors and TAs only (AFR-LMS-001.2).
    # Student roster is strictly excluded to prevent Observer and peer data leakage.
    staff_memberships = CourseMembership.objects.filter(
        course_id=course_id,
        role__in=[CourseRole.INSTRUCTOR, CourseRole.TA],
        status=MembershipStatus.ACTIVE,
    )
    instructors = [m.user_id for m in staff_memberships if m.role == CourseRole.INSTRUCTOR]
    tas = [m.user_id for m in staff_memberships if m.role == CourseRole.TA]

    return {
        "id": workspace.id,
        "course_id": workspace.course_id,
        "course_code": workspace.course_code,
        "title": workspace.title,
        "syllabus": workspace.syllabus,
        "schedule_info": workspace.schedule_info,
        "instructors": instructors,
        "teaching_assistants": tas,
    }
