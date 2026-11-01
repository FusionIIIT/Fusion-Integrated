"""Domain entities and business validation logic.

Pure Python: no Django, DRF or Celery imports.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from .errors import (
    ConflictOfInterestError,
    IncompleteInventorsError,
    InsufficientJustificationError,
    InvalidDocumentError,
    PreconditionNotMetError,
)

# Document limits
MAX_DOCUMENT_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB (BR-PMS-015)
ALLOWED_DOCUMENT_FORMATS = ("pdf",)  # (BR-PMS-014)

# Review validation
MIN_JUSTIFICATION_LENGTH = 50  # (BR-PMS-030)
ALLOWED_DIRECTOR_DECISIONS = ("Approve", "Reject", "Needs Revision")  # (BR-PMS-029)
ALLOWED_APPEAL_OUTCOMES = (
    "Uphold Rejection",
    "Remand for Amendment",
    "Modify Decision",
)  # (BR-PMS-095)
ALLOWED_PATENTABILITY_RECOMMENDATIONS = (
    "File Patent",
    "Do Not File",
    "Needs Amendment",
)  # (BR-PMS-046)
ALLOWED_RENEWAL_DECISIONS = ("Renew", "Do Not Renew")  # (BR-PMS-061)

DEFAULT_BUDGET_THRESHOLD = Decimal("100000.00")  # Configurable threshold


def validate_document(
    filename: str,
    file_size_bytes: int,
    is_malware_clean: bool = True,
) -> None:
    """Validate document format, size, and malware status (BR-PMS-014, 015, 016)."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_DOCUMENT_FORMATS:
        raise InvalidDocumentError(
            f"Unsupported document format '{ext}'. Only PDF documents are accepted (BR-PMS-014)."
        )

    if file_size_bytes > MAX_DOCUMENT_SIZE_BYTES:
        raise InvalidDocumentError(
            f"Document size ({file_size_bytes} bytes) exceeds the 50 MB limit (BR-PMS-015)."
        )

    if not is_malware_clean:
        raise InvalidDocumentError("Document failed security / malware validation (BR-PMS-016).")


def validate_review_decision(decision: str, justification: str) -> None:
    """Validate Director review decision and minimum justification length (BR-PMS-029, 030)."""
    if decision not in ALLOWED_DIRECTOR_DECISIONS:
        raise PreconditionNotMetError(
            f"Invalid review decision '{decision}'. Must be one of: {ALLOWED_DIRECTOR_DECISIONS} (BR-PMS-029)."
        )

    if not justification or len(justification.strip()) < MIN_JUSTIFICATION_LENGTH:
        raise InsufficientJustificationError(
            f"Justification must be at least {MIN_JUSTIFICATION_LENGTH} characters. "
            f"Provided: {len(justification.strip()) if justification else 0} characters (BR-PMS-030)."
        )


def validate_appeal_submission(status: str, grounds: str, justification: str) -> None:
    """Validate that appeal is filed from Rejected status with grounds & justification (BR-PMS-092, 094)."""
    if status != "rejected":
        raise PreconditionNotMetError(
            f"Appeals can only be filed for applications in 'rejected' status, not '{status}' (BR-PMS-092)."
        )
    if not grounds or not grounds.strip():
        raise PreconditionNotMetError("Appeal grounds are required (BR-PMS-094).")
    if not justification or not justification.strip():
        raise PreconditionNotMetError("Appeal justification is required (BR-PMS-094).")


def validate_appeal_outcome(outcome: str, outcome_justification: str = "") -> None:
    """Validate Director appeal outcome (BR-PMS-095)."""
    if outcome not in ALLOWED_APPEAL_OUTCOMES:
        raise PreconditionNotMetError(
            f"Invalid appeal outcome '{outcome}'. Must be one of: {ALLOWED_APPEAL_OUTCOMES} (BR-PMS-095)."
        )
    if not outcome_justification or len(outcome_justification.strip()) < 10:
        raise InsufficientJustificationError("Appeal decision requires written justification.")


def validate_patentability_opinion(recommendation: str, opinion_text: str) -> None:
    """Validate Attorney patentability opinion (BR-PMS-046)."""
    if recommendation not in ALLOWED_PATENTABILITY_RECOMMENDATIONS:
        raise PreconditionNotMetError(
            f"Invalid recommendation '{recommendation}'. Must be one of: {ALLOWED_PATENTABILITY_RECOMMENDATIONS} (BR-PMS-046)."
        )
    if not opinion_text or not opinion_text.strip():
        raise PreconditionNotMetError("A detailed patentability opinion text is required.")


def validate_budget_components(
    filing_fees: Decimal,
    attorney_fees: Decimal,
    administrative_costs: Decimal,
) -> Decimal:
    """Validate budget line items and compute total cost (BR-PMS-048, 049, 050)."""
    if filing_fees < 0 or attorney_fees < 0 or administrative_costs < 0:
        raise PreconditionNotMetError("Budget line items cannot be negative.")
    return filing_fees + attorney_fees + administrative_costs


def check_budget_escalation(
    total_cost: Decimal,
    threshold: Decimal = DEFAULT_BUDGET_THRESHOLD,
) -> bool:
    """Check if total budget exceeds the configured threshold limit (BR-PMS-051)."""
    return total_cost > threshold


def validate_coinventor_shares(shares: Sequence[Decimal]) -> None:
    """Validate that inventor ownership percentages sum to 100% (BR-PMS-074)."""
    total = sum(shares)
    if total != Decimal("100.00") and total != Decimal("100.0") and total != Decimal("100"):
        raise IncompleteInventorsError(
            f"Total inventor ownership shares must equal 100.00%. Current sum: {total}% (BR-PMS-074)."
        )


def check_director_conflict(
    director_user_id: int,
    applicant_user_id: int,
    coinventor_user_ids: Sequence[int],
) -> None:
    """Validate that Director is not an inventor or co-inventor (BR-PMS-026, BR-PMS-027)."""
    if director_user_id == applicant_user_id:
        raise ConflictOfInterestError(
            f"Director (User {director_user_id}) cannot review an application as primary inventor (BR-PMS-026)."
        )
    if director_user_id in coinventor_user_ids:
        raise ConflictOfInterestError(
            f"Director (User {director_user_id}) cannot review an application as co-inventor (BR-PMS-026)."
        )


def validate_filing_preconditions(
    *,
    status: str,
    budget_status: str,
    all_agreements_complete: bool,
    is_international: bool = False,
    international_justification: str = "",
) -> None:
    """Validate all preconditions before external filing is permitted (BR-PMS-020, 056, 078, 128)."""
    allowed_statuses = {"budget_approved", "attorney_assigned", "approved", "pre_filing_satisfied"}
    if status not in allowed_statuses:
        raise PreconditionNotMetError(
            f"Application status '{status}' cannot be filed externally. Must be approved/budget approved (BR-PMS-128)."
        )

    if budget_status != "approved":
        raise PreconditionNotMetError(
            f"Budget must be approved before external filing. Current budget status: '{budget_status}' (BR-PMS-128)."
        )

    if not all_agreements_complete:
        raise PreconditionNotMetError(
            "All inventor agreements and consents must be complete before external filing (BR-PMS-020, BR-PMS-078)."
        )

    if is_international and (
        not international_justification or not international_justification.strip()
    ):
        raise PreconditionNotMetError(
            "International filings require additional justification recorded in PMS (BR-PMS-056)."
        )
