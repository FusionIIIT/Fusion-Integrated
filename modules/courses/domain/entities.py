"""Pure Python domain entities and validation rules."""
from __future__ import annotations

from dataclasses import dataclass

from modules.courses.domain.errors import InvalidCourseDataError, UnauthorizedCourseActionError

ALLOWED_MEMBERSHIP_ROLES = frozenset({"instructor", "ta", "student", "observer"})


@dataclass(frozen=True)
class WorkspaceUpdateDTO:
    title: str | None = None
    description: str | None = None
    syllabus: str | None = None
    schedule: str | None = None
    is_published: bool | None = None
    allow_ta_announcements: bool | None = None

    def validate(self) -> None:
        if self.title is not None and not self.title.strip():
            raise InvalidCourseDataError("Course title cannot be empty.")


def validate_faculty_editor(role: str | None) -> None:
    """Enforce that only assigned faculty instructors can edit workspace details (AFR-LMS-002.1, BR-LMS-004)."""
    if role != "instructor":
        raise UnauthorizedCourseActionError(
            "Only assigned faculty instructors may configure course workspace details."
        )


def validate_membership_role(role: str) -> None:
    if role not in ALLOWED_MEMBERSHIP_ROLES:
        raise InvalidCourseDataError(f"Unknown membership role: {role!r}")
