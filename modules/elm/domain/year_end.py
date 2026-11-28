"""Year-end arithmetic (BR-EL-002..009)."""
from __future__ import annotations

from decimal import Decimal


def vl_to_el(unused_vl: Decimal, ratio: Decimal) -> Decimal:
    if unused_vl <= 0:
        return Decimal("0")
    return (unused_vl / ratio).quantize(Decimal("0.01"))
