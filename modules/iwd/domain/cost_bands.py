"""Cost-band classification logic for IWD estimates.

Implements:
- BR-IWD-003: Cost-band routing
- CFR-IWD-04: Estimate classification and routing
- AFR-IWD-014: Cost-band classification

Thresholds:
- Low-cost:  total < Rs. 25,000
- Mid-range: Rs. 25,000 <= total <= Rs. 2,50,000
- High-cost: total > Rs. 2,50,000
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from enum import Enum


class CostBand(str, Enum):
    """Authoritative cost bands governing approval routing (BR-IWD-003)."""

    LOW = "low_cost"
    MID = "mid_range"
    HIGH = "high_cost"


LOW_COST_LIMIT: Decimal = Decimal("25000.00")
MID_COST_LIMIT: Decimal = Decimal("250000.00")


def classify_cost_band(amount: Decimal | str | int | float) -> CostBand:
    """Classify an estimate amount into its authoritative approval cost band.

    Args:
        amount: Total estimated cost as Decimal, str, int, or float.

    Returns:
        CostBand enum value (LOW, MID, or HIGH).

    Raises:
        ValueError: If amount is negative or cannot be parsed as a valid Decimal.
    """
    try:
        dec_amount = Decimal(str(amount))
    except (InvalidOperation, TypeError) as err:
        raise ValueError(f"Invalid monetary amount: {amount!r}") from err

    if dec_amount < Decimal("0.00"):
        raise ValueError(f"Estimate amount cannot be negative: {dec_amount}")

    if dec_amount < LOW_COST_LIMIT:
        return CostBand.LOW
    elif dec_amount <= MID_COST_LIMIT:
        return CostBand.MID
    else:
        return CostBand.HIGH

