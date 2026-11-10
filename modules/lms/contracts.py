"""Public contract for the LMS module.

Other modules may only call functions defined here (ADR-0012, ADR-0013).
Cross-module getters must be plural (take a sequence of ids).
"""
from collections.abc import Sequence
from typing import Any
from django.utils import timezone
from modules.lms.models import (
    Course,
    CourseMembership,
    Assignment,
    AssignmentSubmission,
)


def get_courses_by_ids(course_ids: Sequence[int]) -> list[dict[str, Any]]:
    """Return course metadata for a sequence of course IDs."""
    courses = Course.objects.filter(id__in=course_ids)
    return [
        {
            "id": c.id,
            "code": c.code,
            "name": c.name,
            "academic_year": c.academic_year,
            "semester": c.semester,
            "is_active": c.is_active,
        }
        for c in courses
    ]


def get_user_courses(user_ids: Sequence[int]) -> dict[int, list[dict[str, Any]]]:
    """Return all active courses for each given user ID."""
    memberships = CourseMembership.objects.filter(
        user_id__in=user_ids, is_active=True
    ).select_related("course")
    out: dict[int, list[dict[str, Any]]] = {uid: [] for uid in user_ids}
    for m in memberships:
        out[m.user_id].append(
            {
                "course_id": m.course.id,
                "code": m.course.code,
                "name": m.course.name,
                "role": m.role,
                "is_primary_instructor": m.is_primary_instructor,
            }
        )
    return out


def get_student_course_ids(student_user_ids: Sequence[int]) -> dict[int, list[int]]:
    """Return mapping of student_user_id -> list of enrolled course IDs."""
    memberships = CourseMembership.objects.filter(
        user_id__in=student_user_ids, role="student", is_active=True
    )
    out: dict[int, list[int]] = {uid: [] for uid in student_user_ids}
    for m in memberships:
        out[m.user_id].append(m.course_id)
    return out


def get_pending_submission_counts(student_user_ids: Sequence[int]) -> dict[int, int]:
    """Return mapping of student_user_id -> count of upcoming published unsubmitted assignments."""
    out: dict[int, int] = {uid: 0 for uid in student_user_ids}
    student_courses = get_student_course_ids(student_user_ids)
    all_course_ids = {cid for cids in student_courses.values() for cid in cids}
    if not all_course_ids:
        return out

    active_assignments = list(
        Assignment.objects.filter(
            course_id__in=all_course_ids,
            status="published",
        ).values("id", "course_id")
    )
    submissions = AssignmentSubmission.objects.filter(
        student_user_id__in=student_user_ids
    ).values_list("student_user_id", "assignment_id")

    submitted_set = set(submissions)

    for uid in student_user_ids:
        user_courses = set(student_courses.get(uid, []))
        user_asgns = [a["id"] for a in active_assignments if a["course_id"] in user_courses]
        unsubmitted = [aid for aid in user_asgns if (uid, aid) not in submitted_set]
        out[uid] = len(unsubmitted)

    return out
