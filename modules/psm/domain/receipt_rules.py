# Delivery receipt, partial receipt, and stock-posting gates (BR-PSM-009, 022, 026).
from __future__ import annotations

from modules.psm.domain.errors import ConflictRuleError, ValidationRuleError


def validate_grn_quantities(
    *,
    ordered_quantity: int,
    previously_accepted: int,
    received_quantity: int,
    accepted_quantity: int,
    rejected_quantity: int,
) -> str:
    """Validate GRN quantities and return resulting GRN status (BR-PSM-022, BR-PSM-026)."""
    if received_quantity <= 0:
        raise ValidationRuleError(
            "Received quantity must be greater than zero.", code="grn_received_invalid"
        )
    if accepted_quantity < 0 or rejected_quantity < 0:
        raise ValidationRuleError(
            "Accepted and rejected quantities cannot be negative.", code="grn_negative_qty"
        )
    if accepted_quantity + rejected_quantity != received_quantity:
        raise ValidationRuleError(
            "Accepted plus rejected quantity must equal received quantity.",
            code="grn_quantity_mismatch",
        )
    if previously_accepted + accepted_quantity > ordered_quantity:
        remaining = max(0, ordered_quantity - previously_accepted)
        raise ConflictRuleError(
            f"Accepted ({accepted_quantity}) exceeds remaining undelivered ({remaining}).",
            code="grn_exceeds_ordered",
        )
    if accepted_quantity == 0:
        return "rejected"
    if previously_accepted + accepted_quantity < ordered_quantity or rejected_quantity > 0:
        return "partial"
    return "accepted"


def ensure_can_post_stock(
    *, accepted_quantity: int, has_open_discrepancy: bool, already_posted: bool
) -> None:
    """Enforce BR-PSM-009 and BR-PSM-026 before final stock ledger posting."""
    if already_posted:
        raise ConflictRuleError(
            "Stock has already been posted for this receipt.", code="stock_already_posted"
        )
    if accepted_quantity <= 0:
        raise ConflictRuleError(
            "Cannot post stock for a receipt with zero accepted quantity.",
            code="no_accepted_quantity",
        )
    if has_open_discrepancy:
        raise ConflictRuleError(
            "Resolve the open discrepancy case before confirming final stock posting.",
            code="unresolved_discrepancy",
        )
