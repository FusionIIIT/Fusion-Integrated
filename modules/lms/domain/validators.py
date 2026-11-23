"""Pure Python domain validation rules."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from modules.lms.domain.constants import MaterialType, SubmissionType


class DomainValidationError(ValueError):
    """Raised when a business constraint or payload validation fails."""


def validate_material_payload(
    material_type: str,
    content_text: str | None,
    external_url: str | None,
    has_file: bool,
) -> None:
    if material_type not in MaterialType.ALL:
        raise DomainValidationError(
            f"Invalid material type: {material_type}. "
            "Select a supported type (note, link, or file)."
        )

    if material_type == MaterialType.NOTE and not (content_text and content_text.strip()):
        raise DomainValidationError(
            "Notes must contain non-empty content_text. Provide text content for the note."
        )

    if material_type == MaterialType.LINK and not (external_url and external_url.strip()):
        raise DomainValidationError(
            "Links must specify an external_url. Provide a valid URL for the resource."
        )

    if material_type == MaterialType.FILE and not has_file:
        raise DomainValidationError(
            "File materials must include a file attachment. Upload a valid document file."
        )


def validate_assignment_config(
    title: str,
    instructions: str,
    points_possible: Decimal | float | int,
    submission_type: str,
    due_date: datetime,
    release_date: datetime | None,
) -> None:
    if not (title and title.strip()):
        raise DomainValidationError(
            "Assignment title cannot be empty. Provide a descriptive title for the assignment."
        )

    if not (instructions and instructions.strip()):
        raise DomainValidationError(
            "Assignment instructions cannot be empty. "
            "Provide detailed instructions for the assignment."
        )

    if Decimal(str(points_possible)) <= 0:
        raise DomainValidationError(
            "Points possible must be greater than zero. Specify a positive point value."
        )

    if submission_type not in SubmissionType.ALL:
        raise DomainValidationError(
            f"Invalid submission type: {submission_type}. Choose text, link, or file."
        )

    if release_date and due_date < release_date:
        raise DomainValidationError(
            "Due date must be after release date. "
            "Set a deadline that occurs after the release timestamp."
        )


def validate_submission_payload(
    submission_type: str,
    content_text: str | None,
    content_link: str | None,
    has_file: bool,
) -> None:
    if submission_type == SubmissionType.TEXT and not (content_text and content_text.strip()):
        raise DomainValidationError(
            "Text submissions must contain content_text. Enter your response in the text field."
        )

    if submission_type == SubmissionType.LINK and not (content_link and content_link.strip()):
        raise DomainValidationError(
            "Link submissions must specify content_link. Enter a valid submission URL."
        )

    if submission_type == SubmissionType.FILE and not has_file:
        raise DomainValidationError(
            "File submissions must include a file attachment. Upload your submission document."
        )


def validate_grade_points(
    points_awarded: Decimal | float | int,
    points_possible: Decimal | float | int,
) -> None:
    awarded = Decimal(str(points_awarded))
    possible = Decimal(str(points_possible))
    if awarded < 0:
        raise DomainValidationError(
            "Points awarded cannot be negative. Provide a score of zero or greater."
        )
    if awarded > possible:
        raise DomainValidationError(
            f"Points awarded ({awarded}) cannot exceed points possible ({possible}). "
            "Adjust the score within allowed bounds."
        )
