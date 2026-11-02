"""Pure domain entities and validation rules for LMS Course Workspace and Materials."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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


class MaterialType:
    FILE: Final[str] = "file"
    LINK: Final[str] = "link"
    NOTE: Final[str] = "note"

    ALL: Final[frozenset[str]] = frozenset({FILE, LINK, NOTE})


class SectionType:
    MODULE: Final[str] = "module"
    WEEK: Final[str] = "week"

    ALL: Final[frozenset[str]] = frozenset({MODULE, WEEK})


class MaterialStatus:
    DRAFT: Final[str] = "draft"
    PUBLISHED: Final[str] = "published"
    SCHEDULED: Final[str] = "scheduled"

    ALL: Final[frozenset[str]] = frozenset({DRAFT, PUBLISHED, SCHEDULED})


@dataclass(frozen=True)
class CourseDetails:
    code: str
    title: str
    description: str = ""
    syllabus: str = ""
    schedule: str = ""
    status: str = CourseStatus.PUBLISHED


@dataclass(frozen=True)
class MaterialDetails:
    title: str
    section_title: str
    material_type: str = MaterialType.FILE
    section_type: str = SectionType.MODULE
    status: str = MaterialStatus.PUBLISHED
    description: str = ""
    link_url: str = ""
    content: str = ""
    release_at: datetime | None = None
    order: int = 0


@dataclass(frozen=True)
class AnnouncementDetails:
    title: str
    content: str



def validate_course_details(*, title: str, status: str) -> None:
    """Validate course workspace configuration parameters."""
    if not title or not title.strip():
        raise LMSRuleError("Course title cannot be empty.")
    if len(title.strip()) > 200:
        raise LMSRuleError("Course title cannot exceed 200 characters.")
    if status not in CourseStatus.ALL:
        choices = sorted(CourseStatus.ALL)
        raise LMSRuleError(f"Invalid course status: '{status}'. Must be one of {choices}.")


def validate_material_details(
    *,
    title: str,
    section_title: str,
    material_type: str,
    section_type: str,
    status: str,
    link_url: str = "",
    content: str = "",
    release_at: datetime | None = None,
) -> None:
    """Validate course material parameters according to CFR-LMS-003 and BR-LMS-006."""
    if not title or not title.strip():
        raise LMSRuleError("Material title cannot be empty.")
    if len(title.strip()) > 200:
        raise LMSRuleError("Material title cannot exceed 200 characters.")

    if not section_title or not section_title.strip():
        raise LMSRuleError("Section title cannot be empty.")
    if len(section_title.strip()) > 100:
        raise LMSRuleError("Section title cannot exceed 100 characters.")

    if material_type not in MaterialType.ALL:
        choices = sorted(MaterialType.ALL)
        raise LMSRuleError(
            f"Invalid material type: '{material_type}'. Must be one of {choices}."
        )

    if section_type not in SectionType.ALL:
        choices = sorted(SectionType.ALL)
        raise LMSRuleError(
            f"Invalid section type: '{section_type}'. Must be one of {choices}."
        )

    if status not in MaterialStatus.ALL:
        choices = sorted(MaterialStatus.ALL)
        raise LMSRuleError(
            f"Invalid material status: '{status}'. Must be one of {choices}."
        )

    if status == MaterialStatus.SCHEDULED and release_at is None:
        raise LMSRuleError("Scheduled material requires a valid release date and time.")

    if material_type == MaterialType.LINK:
        stripped_url = link_url.strip() if link_url else ""
        if not stripped_url:
            raise LMSRuleError("Link materials require a valid URL.")
        if not stripped_url.startswith(("http://", "https://")):
            raise LMSRuleError("Link URL must start with 'http://' or 'https://'.")

    if material_type == MaterialType.NOTE and (not content or not content.strip()):
        raise LMSRuleError("Note materials require content text.")


def validate_announcement_details(*, title: str, content: str) -> None:
    """Validate course announcement parameters according to CFR-LMS-005."""
    if not title or not title.strip():
        raise LMSRuleError("Announcement title cannot be empty.")
    if len(title.strip()) > 200:
        raise LMSRuleError("Announcement title cannot exceed 200 characters.")
    if not content or not content.strip():
        raise LMSRuleError("Announcement content cannot be empty.")


