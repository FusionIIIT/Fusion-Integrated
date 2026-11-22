from decimal import Decimal
from typing import Any


class ValidationError(ValueError):
    """Domain validation error carrying specific requirement failure information."""


def validate_application_data(data: dict[str, Any]) -> None:
    """Validate mandatory fields required for patent application (BR-PMS-017)."""
    title = data.get("title", "")
    if not title or not str(title).strip():
        raise ValidationError("Application title is required and cannot be empty or whitespace.")

    abstract = data.get("abstract", "")
    if not abstract or not str(abstract).strip():
        raise ValidationError("Application abstract is required.")

    claims = data.get("claims", "")
    if not claims or not str(claims).strip():
        raise ValidationError("Patent claims are required before submission.")


def validate_inventor_shares(inventors_data: list[dict[str, Any]]) -> None:
    """Validate that inventor shares sum to exactly 100.00% and each is positive (BR-PMS-002)."""
    if not inventors_data:
        return

    total = Decimal("0.00")
    for inv in inventors_data:
        share = Decimal(str(inv.get("contribution_percentage", 0)))
        if share <= Decimal("0.00") or share > Decimal("100.00"):
            raise ValidationError(
                f"Inventor contribution percentage ({share}%) must be between 0.01% and 100.00%."
            )
        total += share

    if total != Decimal("100.00"):
        raise ValidationError(
            f"Total inventor contribution shares must sum exactly to 100.00% (current sum: {total}%)."
        )


def validate_document_size(file_size_bytes: int) -> None:
    """Validate that application supporting document does not exceed 50 MB limit (BR-PMS-015)."""
    max_bytes = 50 * 1024 * 1024  # 50 MB
    if file_size_bytes > max_bytes:
        raise ValidationError(
            f"Document size ({file_size_bytes} bytes) exceeds maximum allowable limit of 50 MB."
        )


def validate_no_conflict_of_interest(applicant_id: int, reviewer_id: int, co_inventor_ids: list[int]) -> None:
    """Enforce conflict-of-interest prevention: reviewer/director cannot be inventor (BR-PMS-025)."""
    if reviewer_id == applicant_id:
        raise ValidationError(
            f"Conflict of interest detected: Reviewer user #{reviewer_id} is the applicant."
        )
    if reviewer_id in co_inventor_ids:
        raise ValidationError(
            f"Conflict of interest detected: Reviewer user #{reviewer_id} is a listed co-inventor."
        )


def validate_pre_filing_agreements(inventors: list[Any]) -> None:
    """Enforce prerequisite that all co-inventor agreements must be signed prior to filing (BR-PMS-020)."""
    unsigned = [inv for inv in inventors if not getattr(inv, "agreement_signed", False)]
    if unsigned:
        names = ", ".join(getattr(inv, "inventor_name", f"User #{inv.user_id}") for inv in unsigned)
        raise ValidationError(
            f"Cannot proceed with external filing: Co-inventor agreements unsigned for: {names}."
        )
