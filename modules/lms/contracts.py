"""lms public surface. Plural by signature."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CourseSummaryDTO:
    course_id: int
    course_code: str
    title: str
    syllabus: str
    schedule_info: str


@dataclass(frozen=True)
class CourseEnrollmentDTO:
    course_id: int
    user_id: int
    role: str
    status: str


@dataclass(frozen=True)
class StudentGradeSummaryDTO:
    course_id: int
    assignment_id: int
    student_id: int
    points_awarded: float | None
    status: str
    published_at: datetime | None


def get_course_summaries(course_ids: Sequence[int]) -> dict[int, CourseSummaryDTO]:
    """Return course workspace summaries for given course IDs."""
    from modules.lms.models import CourseWorkspace

    ids = {int(i) for i in course_ids if i is not None}
    if not ids:
        return {}
    workspaces = CourseWorkspace.objects.filter(course_id__in=ids)
    return {
        w.course_id: CourseSummaryDTO(
            course_id=w.course_id,
            course_code=w.course_code,
            title=w.title,
            syllabus=w.syllabus,
            schedule_info=w.schedule_info,
        )
        for w in workspaces
    }


def get_user_course_enrollments(
    user_ids: Sequence[int],
) -> dict[int, list[CourseEnrollmentDTO]]:
    """Return active course enrollments grouped by user ID."""
    from modules.lms.models import CourseMembership

    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    memberships = CourseMembership.objects.filter(user_id__in=ids, status="ACTIVE")
    res: dict[int, list[CourseEnrollmentDTO]] = {uid: [] for uid in ids}
    for m in memberships:
        res[m.user_id].append(
            CourseEnrollmentDTO(
                course_id=m.course_id,
                user_id=m.user_id,
                role=m.role,
                status=m.status,
            )
        )
    return res


def get_student_course_grades(
    student_ids: Sequence[int], course_id: int | None = None
) -> dict[int, list[StudentGradeSummaryDTO]]:
    """Return published grade summaries for specified students, optionally filtered by course."""
    from modules.lms.models import SubmissionGrade

    ids = {int(i) for i in student_ids if i is not None}
    if not ids:
        return {}
    qs = SubmissionGrade.objects.filter(
        submission__student_id__in=ids,
        status="PUBLISHED",
    ).select_related("submission")
    if course_id is not None:
        qs = qs.filter(submission__assignment__course_id=course_id)

    res: dict[int, list[StudentGradeSummaryDTO]] = {uid: [] for uid in ids}
    for g in qs:
        cid = course_id if course_id is not None else g.submission.assignment.course_id
        res[g.submission.student_id].append(
            StudentGradeSummaryDTO(
                course_id=cid,
                assignment_id=g.submission.assignment_id,
                student_id=g.submission.student_id,
                points_awarded=float(g.points_awarded) if g.points_awarded is not None else None,
                status=g.status,
                published_at=g.published_at,
            )
        )
    return res
