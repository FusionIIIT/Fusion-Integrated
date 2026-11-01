"""Pure domain entities and validation rules for LMS Course Workspace."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from modules.lms.domain.errors import LMSRuleError


class CourseRole:
    FACULTY: Final[str] = "faculty"
    TA: Final[str] = "ta"
    STUDENT: Final[str] = "student"
    OBSERVER: Final[str] = "observer"

    ALL: Final[frozenset[str]] = frozenset({FACULTY, TA, STUDENT, OBSERVER})
    EDITORS: Final[frozenset[str]] = frozenset({FACULTY})
    READ_ONLY: Final[frozenset[str]] = frozenset({TA, STUDENT, OBSERVER})


class CourseStatus:
    DRAFT: Final[str] = "draft"
    PUBLISHED: Final[str] = "published"

    ALL: Final[frozenset[str]] = frozenset({DRAFT, PUBLISHED})


@dataclass(frozen=True)
class CourseDetails:
    code: str
    title: str
    description: str = ""
    syllabus: str = ""
    schedule: str = ""
    status: str = CourseStatus.PUBLISHED


def validate_course_details(*, title: str, status: str) -> None:
    """Validate course workspace configuration parameters."""
    if not title or not title.strip():
        raise LMSRuleError("Course title cannot be empty.")
    if len(title.strip()) > 200:
        raise LMSRuleError("Course title cannot exceed 200 characters.")
    if status not in CourseStatus.ALL:
        choices = sorted(CourseStatus.ALL)
        raise LMSRuleError(f"Invalid course status: '{status}'. Must be one of {choices}.")
