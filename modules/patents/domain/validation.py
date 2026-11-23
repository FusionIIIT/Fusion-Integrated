from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

MAX_DOCUMENT_SIZE_BYTES = 52_428_800
MIN_JUSTIFICATION_LENGTH = 50

VALID_PATENTABILITY_RECOMMENDATIONS = frozenset({
    "File Patent",
    "Do Not File",
    "Needs Amendment",
})

VALID_APPEAL_OUTCOMES = frozenset({
    "Uphold Rejection",
    "Remand for Amendment",
    "Modify Decision",
    "UPHOLD",
    "REMAND",
    "MODIFY",
})

VALID_REVIEW_DECISIONS = frozenset({
    "Approve",
    "Reject",
    "Needs Revision",
})


class ValidationError(Exception):
    pass


class DocumentFormatError(ValidationError):
    pass


class DocumentSizeError(ValidationError):
    pass


class IncompleteApplicationError(ValidationError):
    pass


class InvalidJustificationError(ValidationError):
    pass


class ConflictOfInterestError(ValidationError):
    pass


class InvalidSharePercentageError(ValidationError):
    pass


class InvalidOpinionRecommendationError(ValidationError):
    pass


class InvalidAppealOutcomeError(ValidationError):
    pass


def validate_application_fields(title: str, abstract: str, description: str, claims: str) -> None:
    if not (title and title.strip()):
        raise IncompleteApplicationError("Enter an application title before submitting.")
    if not (abstract and abstract.strip()):
        raise IncompleteApplicationError("Enter an abstract before submitting.")
    if not (description and description.strip()):
        raise IncompleteApplicationError(
            "Enter a detailed technical description before submitting."
        )
    if not (claims and claims.strip()):
        raise IncompleteApplicationError("Enter the patent claims before submitting.")


def validate_document(
    file_format: str,
    size_bytes: int,
    max_bytes: int = MAX_DOCUMENT_SIZE_BYTES,
) -> None:
    fmt = file_format.lower().lstrip(".")
    if fmt != "pdf":
        raise DocumentFormatError("Upload supporting documents in PDF format.")
    if size_bytes <= 0:
        raise DocumentSizeError("Upload a document that is not empty.")
    if size_bytes > max_bytes:
        raise DocumentSizeError(
            f"Document size ({size_bytes} bytes) exceeds limit of {max_bytes} bytes."
        )


def validate_ownership_shares(shares: Sequence[Decimal | float | int]) -> None:
    if not shares:
        raise InvalidSharePercentageError("Add at least one inventor with an ownership share.")
    total = Decimal("0")
    for s in shares:
        d = Decimal(str(s))
        if d <= 0 or d > 100:
            raise InvalidSharePercentageError(
                "Enter each ownership share as a percentage from 0 to 100."
            )
        total += d
    if total != Decimal("100"):
        raise InvalidSharePercentageError(
            f"Total ownership share must equal 100% (currently {total}%)."
        )


def validate_justification(justification: str, min_length: int = MIN_JUSTIFICATION_LENGTH) -> None:
    actual_len = len(justification.strip()) if justification else 0
    if not justification or actual_len < min_length:
        raise InvalidJustificationError(
            f"Review justification must be at least {min_length} characters (got {actual_len})."
        )


def validate_coi(applicant_user_id: int, reviewer_user_id: int) -> None:
    if applicant_user_id == reviewer_user_id:
        raise ConflictOfInterestError(
            "Assign a reviewer who has not authored or co-invented this application."
        )


def validate_patentability_recommendation(rec: str) -> None:
    if rec not in VALID_PATENTABILITY_RECOMMENDATIONS:
        valid_opts = sorted(VALID_PATENTABILITY_RECOMMENDATIONS)
        raise InvalidOpinionRecommendationError(
            f"Recommendation {rec!r} is invalid. Must be one of: {valid_opts}."
        )


def validate_appeal_outcome(outcome: str) -> None:
    if outcome not in VALID_APPEAL_OUTCOMES:
        valid_opts = sorted(VALID_APPEAL_OUTCOMES)
        raise InvalidAppealOutcomeError(
            f"Appeal outcome {outcome!r} is invalid. Must be one of: {valid_opts}."
        )
