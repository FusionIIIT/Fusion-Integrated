"""LTC and CPDA validation backed only by explicit source fields."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal


class InvalidClaim(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


SUBTYPES = frozenset({"advance", "reimbursement"})


@dataclass(frozen=True)
class LTCSubmission:
    subtype: str
    prescribed_form_reference: str


@dataclass(frozen=True)
class CPDASubmission:
    subtype: str
    purpose: str
    amount: Decimal
    document_references: tuple[str, ...]


def validate_ltc(subtype: str, prescribed_form_reference: str) -> LTCSubmission:
    if subtype not in SUBTYPES:
        raise InvalidClaim("unsupported_subtype", "Choose an LTC advance or reimbursement.")
    if not isinstance(prescribed_form_reference, str) or not prescribed_form_reference.strip():
        raise InvalidClaim("missing_form", "Submit the prescribed LTC form.")
    if len(prescribed_form_reference.strip()) > 250:
        raise InvalidClaim(
            "invalid_form_reference", "Use an LTC form reference of at most 250 characters."
        )
    return LTCSubmission(subtype, prescribed_form_reference.strip())


def validate_cpda(
    subtype: str, purpose: str, amount: Decimal, document_references: Sequence[str]
) -> CPDASubmission:
    if subtype not in SUBTYPES:
        raise InvalidClaim("unsupported_subtype", "Choose a CPDA advance or reimbursement.")
    if not isinstance(purpose, str) or not purpose.strip():
        raise InvalidClaim("missing_purpose", "Give the CPDA request purpose.")
    if not isinstance(amount, Decimal) or not amount.is_finite() or amount <= 0:
        raise InvalidClaim("invalid_amount", "Enter a positive, finite CPDA amount.")
    if isinstance(document_references, (str, bytes)) or not isinstance(
        document_references, Sequence
    ):
        raise InvalidClaim("missing_documents", "Attach the required CPDA documents.")
    documents = tuple(document_references)
    if not documents or any(not isinstance(ref, str) or not ref.strip() for ref in documents):
        raise InvalidClaim("missing_documents", "Attach the required CPDA documents.")
    return CPDASubmission(subtype, purpose.strip(), amount, tuple(ref.strip() for ref in documents))


def validate_financial_recording(
    *, claim_approved: bool, correctness_verified: bool | None
) -> None:
    """An accountant can record observed status, not execute a payment."""
    if claim_approved is not True:
        raise InvalidClaim(
            "not_approved",
            "Only an approved claim can enter financial processing. Contact HR to resolve "
            "this before retrying.",
        )
    if correctness_verified is None:
        raise InvalidClaim(
            "policy_unavailable",
            "Financial correctness criteria are not configured. Contact HR to resolve this "
            "before retrying.",
        )
    if correctness_verified is not True:
        raise InvalidClaim(
            "incorrect_claim",
            "The claim has not passed financial verification. Contact HR to resolve this "
            "before retrying.",
        )
    # This verifies only a recorded status; it does not execute external payment.
