"""LTC and CPDA Claims domain logic (BR-HR-016 to 022, BR-HR-035)."""
from __future__ import annotations

from decimal import Decimal
from enum import Enum

from modules.hreis.domain.exceptions import DomainValidationError


class ClaimType(str, Enum):
    ADVANCE = "advance"
    REIMBURSEMENT = "reimbursement"


class ClaimStatus(str, Enum):
    SUBMITTED = "submitted"
    VERIFIED = "verified"
    FORWARDED = "forwarded"
    APPROVED = "approved"
    REJECTED = "rejected"
    RETURNED = "returned"
    SETTLED = "settled"


class VerificationStatus(str, Enum):
    PENDING = "pending_verification"
    VERIFIED = "verified"
    RETURNED = "returned"
    REJECTED = "rejected"


class PaymentStatus(str, Enum):
    UNPAID = "unpaid"
    PROCESSING = "processing"
    PAID = "paid"



def validate_ltc_submission(
    *,
    request_type: str,
    block_year: str,
    travel_from: str,
    travel_to: str,
    estimated_amount: Decimal,
    claimed_amount: Decimal | None,
) -> None:
    if request_type not in (ClaimType.ADVANCE.value, ClaimType.REIMBURSEMENT.value):
        raise DomainValidationError("Invalid LTC request type. Must be advance or reimbursement.")

    if not block_year or not block_year.strip():
        raise DomainValidationError("LTC block year is required.")

    if not travel_from.strip() or not travel_to.strip():
        raise DomainValidationError("Travel origin and destination are required.")

    if estimated_amount <= Decimal("0.00"):
        raise DomainValidationError("Estimated amount must be greater than zero.")

    if request_type == ClaimType.REIMBURSEMENT.value:
        if claimed_amount is None or claimed_amount <= Decimal("0.00"):
            raise DomainValidationError("Claimed amount is required for LTC reimbursement.")


def validate_cpda_submission(
    *,
    request_type: str,
    purpose: str,
    amount: Decimal,
    available_balance: Decimal,
    supporting_documents: list[str],
) -> None:
    """Validate CPDA required information (BR-HR-020)."""
    if request_type not in (ClaimType.ADVANCE.value, ClaimType.REIMBURSEMENT.value):
        raise DomainValidationError("Invalid CPDA request type. Must be advance or reimbursement.")

    if not purpose or not purpose.strip():
        raise DomainValidationError("Purpose is required for CPDA request.")

    if amount <= Decimal("0.00"):
        raise DomainValidationError("CPDA request amount must be greater than zero.")

    if amount > available_balance:
        raise DomainValidationError(
            f"Requested amount ({amount}) exceeds available CPDA balance ({available_balance})."
        )

    if not supporting_documents:
        raise DomainValidationError("Supporting documents are required for CPDA request (BR-HR-020).")


def validate_financial_settlement(
    *,
    passed_amount: Decimal,
    reference_id: str,
) -> None:
    """Verify financial correctness before recording settlement (BR-HR-035)."""
    if passed_amount <= Decimal("0.00"):
        raise DomainValidationError("Settlement amount must be positive.")

    if not reference_id or not reference_id.strip():
        raise DomainValidationError("Settlement reference / voucher number is required.")
