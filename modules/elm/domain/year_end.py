"""Pure year-end arithmetic for BR-EL-007."""
from decimal import Decimal, ROUND_DOWN


def vl_to_el(vl_days: Decimal) -> Decimal:
    """Convert unused VL to EL at 2:1, preserving fractional conversion."""
    return (vl_days / Decimal("2")).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
