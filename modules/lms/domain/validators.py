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
        raise DomainValidationError(f"Invalid material type: {material_type}")

    if material_type == MaterialType.NOTE and not (content_text and content_text.strip()):
        raise DomainValidationError("Notes must contain non-empty content_text.")

    if material_type == MaterialType.LINK and not (external_url and external_url.strip()):
        raise DomainValidationError("Links must specify an external_url.")

    if material_type == MaterialType.FILE and not has_file:
        raise DomainValidationError("File materials must include a file attachment.")


def validate_assignment_config(
    title: str,
    instructions: str,
    points_possible: Decimal | float | int,
    submission_type: str,
    due_date: datetime,
    release_date: datetime | None,
) -> None:
    if not (title and title.strip()):
        raise DomainValidationError("Assignment title cannot be empty.")

    if not (instructions and instructions.strip()):
        raise DomainValidationError("Assignment instructions cannot be empty.")

    if Decimal(str(points_possible)) <= 0:
        raise DomainValidationError("Points possible must be greater than zero.")

    if submission_type not in SubmissionType.ALL:
        raise DomainValidationError(f"Invalid submission type: {submission_type}")

    if release_date and due_date < release_date:
        raise DomainValidationError("Due date must be after release date.")


def validate_submission_payload(
    submission_type: str,
    content_text: str | None,
    content_link: str | None,
    has_file: bool,
) -> None:
    if submission_type == SubmissionType.TEXT and not (content_text and content_text.strip()):
        raise DomainValidationError("Text submissions must contain content_text.")

    if submission_type == SubmissionType.LINK and not (content_link and content_link.strip()):
        raise DomainValidationError("Link submissions must specify content_link.")

    if submission_type == SubmissionType.FILE and not has_file:
        raise DomainValidationError("File submissions must include a file attachment.")


def validate_grade_points(
    points_awarded: Decimal | float | int,
    points_possible: Decimal | float | int,
) -> None:
    awarded = Decimal(str(points_awarded))
    possible = Decimal(str(points_possible))
    if awarded < 0:
        raise DomainValidationError("Points awarded cannot be negative.")
    if awarded > possible:
        raise DomainValidationError(
            f"Points awarded ({awarded}) cannot exceed points possible ({possible})."
        )
