"""Pure domain entities and validation rules for LMS Course Workspace and Materials."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Final

from modules.lms.domain.errors import (
    DeadlineWindowError,
    ExtensionDeniedError,
    LMSRuleError,
    ScoreValidationError,
    SubmissionTypeError,
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


class SubmissionStatus:
    SUBMITTED: Final[str] = "submitted"
    LATE: Final[str] = "late"
    MISSING: Final[str] = "missing"

    ALL: Final[frozenset[str]] = frozenset({SUBMITTED, LATE, MISSING})


class GradeStatus:
    DRAFT: Final[str] = "draft"
    RELEASED: Final[str] = "released"

    ALL: Final[frozenset[str]] = frozenset({DRAFT, RELEASED})


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


@dataclass(frozen=True)
class SubmissionDetails:
    assignment_id: int
    student_user_id: int
    submission_type: str
    status: str = SubmissionStatus.SUBMITTED
    file_name: str = ""
    file_size: int | None = None
    content_text: str = ""
    link_url: str = ""
    attempt_number: int = 1


@dataclass(frozen=True)
class EvaluationDetails:
    submission_id: int
    assignment_id: int
    student_user_id: int
    score: Decimal
    graded_by_user_id: int
    status: str = GradeStatus.DRAFT
    graded_at: datetime | None = None



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


def validate_submission_details(
    *,
    assignment_submission_type: str,
    submission_type: str,
    file: Any = None,
    content_text: str = "",
    link_url: str = "",
) -> None:
    """Validate student submission parameters against assignment configuration.

    Enforces BR-LMS-012 (Submission-type conformity) and AFR-LMS-008.1.
    """
    if submission_type not in SubmissionType.ALL:
        choices = sorted(SubmissionType.ALL)
        raise SubmissionTypeError(
            f"Invalid submission type: '{submission_type}'. Must be one of {choices}."
        )

    if submission_type != assignment_submission_type:
        raise SubmissionTypeError(
            f"Submission type '{submission_type}' does not match the assignment's "
            f"configured type '{assignment_submission_type}'."
        )

    if submission_type == SubmissionType.FILE:
        if not file:
            raise SubmissionTypeError("File submission requires an uploaded file attachment.")
        f_size = getattr(file, "size", None)
        if f_size is not None and f_size > 50 * 1024 * 1024:
            raise SubmissionTypeError("Submission file size exceeds maximum limit of 50 MB.")

    elif submission_type == SubmissionType.TEXT:
        cleaned_text = content_text.strip() if content_text else ""
        if not cleaned_text:
            raise SubmissionTypeError("Text submission requires non-empty content text.")
        if len(cleaned_text) > 50000:
            raise SubmissionTypeError("Text submission content cannot exceed 50,000 characters.")

    elif submission_type == SubmissionType.LINK:
        cleaned_url = link_url.strip() if link_url else ""
        if not cleaned_url:
            raise SubmissionTypeError("Link submission requires a valid URL.")
        if not cleaned_url.startswith(("http://", "https://")):
            raise SubmissionTypeError("Link URL must start with 'http://' or 'https://'.")
        if len(cleaned_url) > 500:
            raise SubmissionTypeError("Link URL cannot exceed 500 characters.")


def validate_evaluation_score(*, score: Any, points_possible: Decimal) -> Decimal:
    """Validate numeric score against assignment points possible and precision constraints.

    Enforces:
    - Score is provided and convertable to Decimal.
    - Score cannot be negative (score >= 0.00).
    - Score cannot exceed points_possible (CFR-LMS-010, AFR-LMS-010.1).
    - Score has at most 2 decimal places.
    """
    if score is None:
        raise ScoreValidationError("Score is required.")
    try:
        dec_score = Decimal(str(score))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ScoreValidationError(f"Invalid numeric score: '{score}'.") from exc

    if dec_score < Decimal("0.00"):
        raise ScoreValidationError("Score cannot be negative.")

    if points_possible is not None and dec_score > points_possible:
        raise ScoreValidationError(
            f"Score ({dec_score}) cannot exceed maximum points possible ({points_possible})."
        )

    # Check decimal precision (at most 2 decimal places)
    exp = dec_score.as_tuple().exponent
    if isinstance(exp, int) and exp < -2:
        raise ScoreValidationError("Score cannot have more than 2 decimal places.")

    return dec_score.quantize(Decimal("0.01"))
