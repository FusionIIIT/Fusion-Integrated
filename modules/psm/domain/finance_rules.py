# Three-way match and payment eligibility rules (BR-PSM-012, 017, 018, 022).
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from modules.psm.domain.errors import ConflictRuleError, ValidationRuleError


@dataclass(frozen=True)
class ThreeWayMatchInput:
    po_ordered_quantity: int
    po_unit_price: Decimal
    po_total_amount: Decimal
    confirmed_accepted_quantity: int
    billed_quantity: int
    billed_amount: Decimal
    has_open_discrepancy: bool
    vendor_verified: bool
    partial_payment_enabled: bool


@dataclass(frozen=True)
class MatchOutcome:
    matched: bool
    eligible_amount: Decimal
    hold_reason: str = ""


def three_way_match(data: ThreeWayMatchInput) -> MatchOutcome:
    """Evaluate PO, confirmed GRN, and invoice (BR-PSM-017, 018, 022)."""
    if not data.vendor_verified:
        return MatchOutcome(False, Decimal("0.00"), "Vendor master verification is incomplete.")
    if data.has_open_discrepancy:
        return MatchOutcome(
            False,
            Decimal("0.00"),
            "An unresolved delivery discrepancy blocks invoice verification.",
        )
    if data.confirmed_accepted_quantity <= 0:
        return MatchOutcome(
            False, Decimal("0.00"), "No confirmed accepted delivery receipt exists for this PO."
        )
    if data.billed_quantity > data.confirmed_accepted_quantity:
        return MatchOutcome(
            False,
            Decimal("0.00"),
            (
                f"Billed ({data.billed_quantity}) exceeds confirmed "
                f"({data.confirmed_accepted_quantity})."
            ),
        )
    expected_amount = (Decimal(data.billed_quantity) * data.po_unit_price).quantize(Decimal("0.01"))
    if data.billed_amount > expected_amount:
        return MatchOutcome(
            False,
            Decimal("0.00"),
            f"Billed amount ({data.billed_amount}) exceeds PO value ({expected_amount}).",
        )
    is_partial = (
        data.billed_quantity < data.po_ordered_quantity or data.billed_amount < data.po_total_amount
    )
    if is_partial and not data.partial_payment_enabled:
        return MatchOutcome(
            False, Decimal("0.00"), "Partial payments are disabled under the active PSM policy."
        )
    return MatchOutcome(True, data.billed_amount)


def validate_payment_release(
    *,
    invoice_status: str,
    eligible_amount: Decimal,
    already_paid: Decimal,
    requested_amount: Decimal,
    vendor_verified: bool,
    has_open_discrepancy: bool,
    partial_payment_enabled: bool,
) -> bool:
    """Validate payment release and return True when partial (BR-PSM-017, 022)."""
    if requested_amount <= Decimal("0"):
        raise ValidationRuleError(
            "Payment amount must be greater than zero.", code="invalid_payment_amount"
        )
    if not vendor_verified:
        raise ConflictRuleError(
            "Vendor is unverified; complete vendor verification before releasing payment.",
            code="vendor_unverified",
        )
    if has_open_discrepancy:
        raise ConflictRuleError(
            "Resolve the open discrepancy case before releasing payment.",
            code="unresolved_discrepancy",
        )
    if invoice_status not in ("verified", "partially_paid"):
        raise ConflictRuleError(
            f"Invoice in state '{invoice_status}' is not eligible for payment; verify it first.",
            code="invoice_not_verified",
        )
    remaining = (eligible_amount - already_paid).quantize(Decimal("0.01"))
    if requested_amount > remaining:
        raise ConflictRuleError(
            f"Payment ({requested_amount}) exceeds remaining eligible balance ({remaining}).",
            code="payment_exceeds_eligible",
        )
    is_partial = requested_amount < remaining
    if is_partial and not partial_payment_enabled:
        raise ConflictRuleError(
            "Partial payments are disabled under the active PSM policy.",
            code="partial_payment_disabled",
        )
    return is_partial
