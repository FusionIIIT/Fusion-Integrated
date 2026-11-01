"""Service layer for Departmental TA and Supervisor Allocations and Announcements."""
from __future__ import annotations

from django.db import transaction
from core.api.exceptions import BadRequestError, NotFoundError

from modules.department.models.allocation import (
    ThesisSupervisorAllocation,
    TAAllocation,
)
from modules.department.models.announcement import DepartmentAnnouncement


@transaction.atomic
def allocate_thesis_supervisor(
    actor,
    student_id: int,
    student_name: str,
    programme: str,
    supervisor_id: int,
    supervisor_name: str,
    co_supervisor_name: str = "",
    thesis_topic: str = "",
    academic_year: str = "2026-27",
    department: str = "",
) -> ThesisSupervisorAllocation:
    """Record a departmental thesis supervisor allocation (AFR-OAP-043)."""
    if not student_id or not student_name.strip():
        raise BadRequestError("Student ID and Student Name are required.", code="missing_student")
    if not supervisor_id or not supervisor_name.strip():
        raise BadRequestError("Supervisor ID and Supervisor Name are required.", code="missing_supervisor")

    alloc, _ = ThesisSupervisorAllocation.objects.update_or_create(
        student_id=student_id,
        academic_year=academic_year,
        defaults={
            "student_name": student_name.strip(),
            "programme": programme.strip(),
            "department": department.strip(),
            "supervisor_id": supervisor_id,
            "supervisor_name": supervisor_name.strip(),
            "co_supervisor_name": co_supervisor_name.strip(),
            "thesis_topic": thesis_topic.strip(),
            "status": "ACTIVE",
        },
    )
    return alloc


@transaction.atomic
def allocate_teaching_assistant(
    actor,
    student_id: int,
    student_name: str,
    course_code: str,
    course_name: str,
    faculty_id: int | None = None,
    faculty_name: str = "",
    programme: str = "M.Tech",
    semester: str = "Monsoon",
    academic_year: str = "2026-27",
    hours_per_week: int = 8,
    department: str = "",
) -> TAAllocation:
    """Record a departmental TA assignment (AFR-OAP-044)."""
    if not student_id or not student_name.strip():
        raise BadRequestError("Student ID and Student Name are required.", code="missing_student")
    if not course_code or not course_code.strip():
        raise BadRequestError("Course code is required.", code="missing_course")

    alloc = TAAllocation.objects.create(
        student_id=student_id,
        student_name=student_name.strip(),
        course_code=course_code.strip().upper(),
        course_name=course_name.strip(),
        faculty_id=faculty_id,
        faculty_name=faculty_name.strip(),
        programme=programme.strip(),
        semester=semester.strip(),
        academic_year=academic_year.strip(),
        hours_per_week=hours_per_week,
        department=department.strip(),
    )
    return alloc


@transaction.atomic
def create_announcement(
    actor,
    title: str,
    content: str,
    department: str = "",
    target_audience: str = "ALL",
    is_pinned: bool = False,
) -> DepartmentAnnouncement:
    """Create a new department announcement."""
    if not title or not title.strip():
        raise BadRequestError("Announcement title is required.", code="missing_title")
    if not content or not content.strip():
        raise BadRequestError("Announcement content is required.", code="missing_content")

    user_id = getattr(actor, "user_id", 0) or getattr(actor, "id", 0)
    user_name = getattr(actor, "display_name", "") or getattr(actor, "username", "Admin")

    return DepartmentAnnouncement.objects.create(
        title=title.strip(),
        content=content.strip(),
        department=department.strip(),
        target_audience=target_audience.strip(),
        posted_by_id=user_id,
        posted_by_name=user_name,
        is_pinned=is_pinned,
    )
