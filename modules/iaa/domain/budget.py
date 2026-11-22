"""Budget arithmetic over the append-only ledger (BR-102)."""
from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal


def available(amounts: Iterable[Decimal]) -> Decimal:
    return sum(amounts, Decimal("0"))


def shortfall(amount: Decimal, available_amount: Decimal) -> Decimal:
    return max(amount - available_amount, Decimal("0"))
