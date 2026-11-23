"""Cost-band classification logic (BR-IWD-003, CFR-IWD-04)."""

from decimal import Decimal

BAND_LOW = "LOW"
BAND_MID = "MID"
BAND_HIGH = "HIGH"

LOW_COST_THRESHOLD = Decimal("25000.00")
MID_COST_MAX_THRESHOLD = Decimal("250000.00")


def classify_band(total_cost: Decimal | float | int | str) -> str:
    """Classify an estimate amount into Low, Mid, or High cost bands."""
    amount = Decimal(str(total_cost))
    if amount < LOW_COST_THRESHOLD:
        return BAND_LOW
    if amount <= MID_COST_MAX_THRESHOLD:
        return BAND_MID
    return BAND_HIGH
