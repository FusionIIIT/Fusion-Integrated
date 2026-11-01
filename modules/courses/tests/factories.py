"""Test factories for the courses module."""
from __future__ import annotations

from modules.courses.models import CourseMembership, CourseWorkspace


def make_workspace(
    *,
    code: str = "CS201",
    title: str = "Data Structures and Algorithms",
    description: str = "Core data structures course",
    semester: str = "Monsoon 2026",
    academic_year: str = "2026-2027",
    credits: int = 4,
    syllabus: str = "1. Arrays 2. Trees 3. Graphs",
    schedule: str = "Mon, Wed 10:00 - 11:30 AM",
    is_published: bool = True,
    allow_ta_announcements: bool = False,
) -> CourseWorkspace:
    return CourseWorkspace.objects.create(
        code=code,
        title=title,
        description=description,
        semester=semester,
        academic_year=academic_year,
        credits=credits,
        syllabus=syllabus,
        schedule=schedule,
        is_published=is_published,
        allow_ta_announcements=allow_ta_announcements,
    )


def add_member(
    workspace: CourseWorkspace,
    user_id: int,
    role: str = "student",
) -> CourseMembership:
    return CourseMembership.objects.create(
        workspace=workspace,
        user_id=user_id,
        role=role,
    )
