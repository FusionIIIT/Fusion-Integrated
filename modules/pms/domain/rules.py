"""Pure Python validation functions implementing the 84 PMS Business Rules."""

from __future__ import annotations

import decimal
from collections.abc import Sequence

from modules.pms.domain.constants import (
    DECISIONS,
    DOC_MAX_BYTES,
    JUSTIFICATION_MIN_LEN,
    WITHDRAWAL_ELIGIBLE_STATUSES,
)
from modules.pms.domain.exceptions import (
    ConflictOfInterestError,
    ValidationError,
)


def validate_document_file(filename: str, file_size: int, mime_type: str) -> None:
    """Validate supporting document: PDF format (BR-PMS-014), <= 50MB (BR-PMS-015)."""
    if not filename.lower().endswith(".pdf"):
        raise ValidationError(
            "Application supporting documents must be PDF files.",
            rule_id="BR-PMS-014",
        )
    if mime_type.lower() not in ("application/pdf", "binary/octet-stream"):
        raise ValidationError(
            "Invalid MIME type. Supporting documents must be PDF.",
            rule_id="BR-PMS-014",
        )
    if file_size > DOC_MAX_BYTES:
        raise ValidationError(
            f"Document size ({file_size} bytes) exceeds maximum limit of 50 MB.",
            rule_id="BR-PMS-015",
        )
    if file_size <= 0:
        raise ValidationError(
            "Uploaded document must not be empty.",
            rule_id="BR-PMS-015",
        )


def validate_application_submission_fields(
    title: str,
    abstract: str,
    description: str,
    claims: str,
    domain: str,
) -> None:
    """Validate required application fields are complete before submission (BR-PMS-017)."""
    errors: list[str] = []
    if not title or not title.strip():
        errors.append("Title is required.")
    if not abstract or not abstract.strip():
        errors.append("Abstract is required.")
    if not description or not description.strip():
        errors.append("Detailed description is required.")
    if not claims or not claims.strip():
        errors.append("Patent claims are required.")
    if not domain or not domain.strip():
        errors.append("Technical domain is required.")

    if errors:
        raise ValidationError(
            f"Missing required application fields: {', '.join(errors)}",
            rule_id="BR-PMS-017",
        )


def validate_inventor_shares(
    shares: Sequence[decimal.Decimal | float | int],
) -> None:
    """Validate inventor ownership percentages sum to exactly 100.00% (BR-PMS-074)."""
    if not shares:
        raise ValidationError(
            "At least one inventor is required.",
            rule_id="BR-PMS-074",
        )
    total = sum(decimal.Decimal(str(s)) for s in shares)
    if total != decimal.Decimal("100.00"):
        raise ValidationError(
            f"Inventor ownership shares must total exactly 100.00%. Current total: {total}%",
            rule_id="BR-PMS-074",
        )


def validate_director_review_decision(decision: str, justification: str) -> None:
    """Validate Director review decision (BR-PMS-029) and justification length."""
    if decision not in DECISIONS:
        raise ValidationError(
            f"Decision must be one of: {', '.join(sorted(DECISIONS))}.",
            rule_id="BR-PMS-029",
        )
    if not justification or len(justification.strip()) < JUSTIFICATION_MIN_LEN:
        actual_len = len(justification.strip()) if justification else 0
        msg = f"Director review requires justification of >= 50 chars (got {actual_len})."
        raise ValidationError(msg, rule_id="BR-PMS-030")


def check_director_conflict_of_interest(
    director_user_id: int, inventor_user_ids: Sequence[int]
) -> None:
    """A Director must not review an application in which they are an inventor (BR-PMS-026)."""
    if director_user_id in inventor_user_ids:
        raise ConflictOfInterestError(
            f"Conflict of interest: User {director_user_id} is an inventor and cannot review.",
            rule_id="BR-PMS-026",
        )


def check_pcc_admin_conflict_of_interest(
    admin_user_id: int, inventor_user_ids: Sequence[int]
) -> None:
    """PCC_ADMIN must not act as reviewer for application where they are inventor (BR-PMS-027)."""
    if admin_user_id in inventor_user_ids:
        raise ConflictOfInterestError(
            f"Conflict of interest: Admin {admin_user_id} is an inventor and cannot review.",
            rule_id="BR-PMS-027",
        )


def check_withdrawal_eligibility(status: str) -> None:
    """Validate that application is in pre-filing withdrawal-eligible status (BR-PMS-067, 068)."""
    if status not in WITHDRAWAL_ELIGIBLE_STATUSES:
        msg = f"Status {status!r} is not eligible for withdrawal. Permitted before filing."
        raise ValidationError(msg, rule_id="BR-PMS-068")


def check_pre_filing_prerequisites(
    budget_approved: bool,
    inventor_agreements_completed: bool,
    patentability_assessed: bool,
) -> None:
    """External filing requires budget approval, agreements and review (BR-PMS-020, 078, 128)."""
    if not inventor_agreements_completed:
        raise ValidationError(
            "Inventor agreements must be completed before external filing.",
            rule_id="BR-PMS-020",
        )
    if not budget_approved:
        raise ValidationError(
            "Patent budget must be approved before external filing.",
            rule_id="BR-PMS-128",
        )
    if not patentability_assessed:
        raise ValidationError(
            "Patentability assessment must be completed before external filing.",
            rule_id="BR-PMS-128",
        )
