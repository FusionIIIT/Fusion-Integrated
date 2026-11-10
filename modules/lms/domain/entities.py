"""Pure domain entities and validation rules for LMS Course Workspace and Materials."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Final

from modules.lms.domain.errors import (
    DeadlineWindowError,
    ExtensionDeniedError,
    LMSRuleError,
)


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


class SubmissionType:
    FILE: Final[str] = "file"
    TEXT: Final[str] = "text"
    LINK: Final[str] = "link"

    ALL: Final[frozenset[str]] = frozenset({FILE, TEXT, LINK})


class AssignmentStatus:
    DRAFT: Final[str] = "draft"
    PUBLISHED: Final[str] = "published"
    SCHEDULED: Final[str] = "scheduled"

    ALL: Final[frozenset[str]] = frozenset({DRAFT, PUBLISHED, SCHEDULED})


class DeadlineWindowStatus:
    NOT_OPEN: Final[str] = "not_open"
    OPEN: Final[str] = "open"
    LATE_ALLOWED: Final[str] = "late_allowed"
    CLOSED: Final[str] = "closed"

    ALL: Final[frozenset[str]] = frozenset({NOT_OPEN, OPEN, LATE_ALLOWED, CLOSED})


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


@dataclass(frozen=True)
class AssignmentDetails:
    title: str
    instructions: str = ""
    submission_type: str = SubmissionType.FILE
    points_possible: Decimal = Decimal("100.00")
    status: str = AssignmentStatus.DRAFT
    due_at: datetime | None = None
    release_at: datetime | None = None
    closes_at: datetime | None = None
    allow_late: bool = False


@dataclass(frozen=True)
class DeadlineInfo:
    assignment_id: int
    original_due_at: datetime | None
    closes_at: datetime | None
    allow_late: bool
    effective_due_at: datetime | None
    is_extended: bool
    extended_due_at: datetime | None = None
    extension_reason: str = ""
    window_status: str = DeadlineWindowStatus.OPEN
    is_submission_allowed: bool = True



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


def validate_assignment_details(
    *,
    title: str,
    submission_type: str,
    status: str,
    points_possible: Decimal | float | int | str | None = None,
    instructions: str = "",
    due_at: datetime | None = None,
    release_at: datetime | None = None,
    closes_at: datetime | None = None,
) -> None:
    """Validate course assignment parameters.

    Adheres to CFR-LMS-006, BR-LMS-009, BR-LMS-010, and BR-LMS-011.
    """
    if not title or not title.strip():
        raise LMSRuleError("Assignment title cannot be empty.")
    if len(title.strip()) > 200:
        raise LMSRuleError("Assignment title cannot exceed 200 characters.")

    if submission_type not in SubmissionType.ALL:
        choices = sorted(SubmissionType.ALL)
        raise LMSRuleError(
            f"Invalid submission type: '{submission_type}'. Must be one of {choices}."
        )

    if status not in AssignmentStatus.ALL:
        choices = sorted(AssignmentStatus.ALL)
        raise LMSRuleError(
            f"Invalid assignment status: '{status}'. Must be one of {choices}."
        )

    if points_possible is not None:
        try:
            pts = Decimal(str(points_possible))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise LMSRuleError("Points possible must be a valid positive number.") from exc
        if pts <= 0:
            raise LMSRuleError("Points possible must be greater than zero.")

    # Publication validation (BR-LMS-009)
    if status in {AssignmentStatus.PUBLISHED, AssignmentStatus.SCHEDULED}:
        if not instructions or not instructions.strip():
            raise LMSRuleError("Published assignment requires instructions.")
        if due_at is None:
            raise LMSRuleError("Published assignment requires a valid due date.")
        if points_possible is None:
            raise LMSRuleError("Published assignment requires points possible.")

    if status == AssignmentStatus.SCHEDULED and release_at is None:
        raise LMSRuleError("Scheduled assignment requires a valid release date and time.")

    if release_at is not None and due_at is not None and release_at > due_at:
        raise LMSRuleError("Assignment release date cannot be after the due date.")

    if closes_at is not None and due_at is not None and closes_at < due_at:
        raise LMSRuleError("Closing cutoff date cannot be earlier than the due date.")


def validate_deadline_window(
    *,
    due_at: datetime | None,
    closes_at: datetime | None = None,
    release_at: datetime | None = None,
    allow_late: bool = False,
) -> tuple[datetime | None, datetime | None, bool]:
    """Validate submission window opening, due, and closing dates."""
    if release_at is not None and due_at is not None and release_at > due_at:
        raise DeadlineWindowError("Assignment release date cannot be after the due date.")
    if closes_at is not None and due_at is None:
        raise DeadlineWindowError(
            "Assignment due date must be set if a closing cutoff is configured."
        )
    if closes_at is not None and due_at is not None and closes_at < due_at:
        raise DeadlineWindowError("Closing cutoff date cannot be earlier than the due date.")
    return due_at, closes_at, allow_late


def validate_extension_details(
    *,
    student_user_id: int,
    extended_due_at: datetime | None,
    assignment_due_at: datetime | None = None,
    original_due_at: datetime | None = None,
    reason: str = "",
) -> tuple[datetime, str]:
    """Validate student deadline extension parameters."""
    if student_user_id <= 0:
        raise ExtensionDeniedError("Valid student user ID is required.")
    if extended_due_at is None:
        raise ExtensionDeniedError("Extended due date cannot be empty.")
    base_due = assignment_due_at if assignment_due_at is not None else original_due_at
    if base_due is not None and extended_due_at <= base_due:
        raise ExtensionDeniedError(
            "Extended due date must be strictly later than the assignment due date."
        )
    cleaned_reason = reason.strip() if reason else ""
    if len(cleaned_reason) > 500:
        raise ExtensionDeniedError("Reason cannot exceed 500 characters.")
    return extended_due_at, cleaned_reason
