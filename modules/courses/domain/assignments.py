"""Pure Python domain entities and validation rules for Course Assignments (CFR-LMS-006, BR-LMS-009, BR-LMS-010)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from modules.courses.domain.errors import InvalidCourseDataError, UnauthorizedCourseActionError


@dataclass(frozen=True)
class AssignmentCreateDTO:
    title: str
    description: str = ""
    instructions: str = ""
    max_points: Decimal = Decimal("100.00")
    due_at: datetime | None = None
    is_published: bool = False

    def validate(self) -> None:
        if not self.title or not self.title.strip():
            raise InvalidCourseDataError("Assignment title cannot be empty.")
        if len(self.title.strip()) > 200:
            raise InvalidCourseDataError("Assignment title cannot exceed 200 characters.")
        if self.max_points is not None and self.max_points < Decimal("0.00"):
            raise InvalidCourseDataError("Assignment max points cannot be negative.")


@dataclass(frozen=True)
class AssignmentUpdateDTO:
    title: str | None = None
    description: str | None = None
    instructions: str | None = None
    max_points: Decimal | None = None
    due_at: datetime | None = None
    clear_due_at: bool = False
    is_published: bool | None = None

    def validate(self) -> None:
        if self.title is not None:
            if not self.title.strip():
                raise InvalidCourseDataError("Assignment title cannot be empty.")
            if len(self.title.strip()) > 200:
                raise InvalidCourseDataError("Assignment title cannot exceed 200 characters.")
        if self.max_points is not None and self.max_points < Decimal("0.00"):
            raise InvalidCourseDataError("Assignment max points cannot be negative.")


def validate_assignment_author(role: str | None) -> None:
    """Enforce that only assigned faculty instructors can author/edit assignments (BR-LMS-004)."""
    if role != "instructor":
        raise UnauthorizedCourseActionError(
            "Only assigned faculty instructors may create, edit, or delete course assignments."
        )
