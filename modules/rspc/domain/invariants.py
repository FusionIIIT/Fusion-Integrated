"""Pure Python Business Invariants and Rules for RSPC."""

from __future__ import annotations

from decimal import Decimal


class InvariantViolationError(ValueError):
    """Raised when a domain invariant or business rule is violated."""


def validate_budget_head_positive(amount: Decimal, head_name: str) -> None:
    """BR-RSPC-035: Budget allocations and amounts must be non-negative."""
    if amount < Decimal("0.00"):
        raise InvariantViolationError(
            f"Budget head '{head_name}' allocation cannot be negative: {amount}"
        )


def validate_disbursement(
    head_name: str, available_balance: Decimal, requested_amount: Decimal
) -> None:
    """BR-RSPC-035: Deficit prohibition - cannot disburse more than available balance."""
    if requested_amount <= Decimal("0.00"):
        raise InvariantViolationError(
            f"Disbursement request must be strictly positive, got: {requested_amount}"
        )
    if requested_amount > available_balance:
        raise InvariantViolationError(
            f"Insufficient balance in budget head '{head_name}': "
            f"requested {requested_amount}, available {available_balance}"
        )


def calculate_institutional_overheads(
    direct_costs: Decimal, overhead_rate_percent: Decimal
) -> Decimal:
    """BR-RSPC-014: Represented policy validation - overheads based on approved rate."""
    if direct_costs < Decimal("0.00") or overhead_rate_percent < Decimal("0.00"):
        raise InvariantViolationError("Cost and overhead percentages must be non-negative.")
    return (direct_costs * overhead_rate_percent / Decimal("100.00")).quantize(Decimal("0.01"))


def validate_extension_request(
    requested_months: int, cumulative_months: int, approver_role: str
) -> None:
    """BR-RSPC-069: Director stage routing for extensions exceeding threshold."""
    if requested_months <= 0:
        raise InvariantViolationError("Extension request must specify at least 1 month.")
    total = cumulative_months + requested_months
    if total > 12 and approver_role.lower() != "director":
        raise InvariantViolationError(
            f"Extensions exceeding 12 cumulative months ({total} months) require Director approval."
        )
