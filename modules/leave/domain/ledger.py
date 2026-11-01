"""The leave ledger: append-only moves, never an edited balance.

A balance column can be edited by a correction; a ledger cannot, because the
correction is another row. Only `signed_days` and `project` are arithmetic -
everything else in the module reads the projection (BR-EL-005, 007, 008, 028).
"""
from __future__ import annotations

from decimal import Decimal

#: Money-style literals, so the signs below are the only place they are decided.
OPENING = "opening"
ACCRUAL = "accrual"
DEBIT = "debit"
CREDIT = "credit"
LAPSE = "lapse"
CONVERSION_OUT = "conversion_out"
CONVERSION_IN = "conversion_in"
ADJUSTMENT = "adjustment"
REVERSAL = "reversal"

POSITIVE = frozenset({OPENING, ACCRUAL, CREDIT, CONVERSION_IN})
NEGATIVE = frozenset({DEBIT, LAPSE, CONVERSION_OUT})

ENTRY_TYPES: tuple[str, ...] = (OPENING, ACCRUAL, DEBIT, CREDIT, LAPSE,
                                CONVERSION_OUT, CONVERSION_IN, ADJUSTMENT, REVERSAL)

ZERO = Decimal("0")


def signed_days(entry_type: str, days: Decimal) -> Decimal:
    """The ledger's sign for an entry type. `days` is always the magnitude."""
    if entry_type in POSITIVE:
        return abs(days)
    if entry_type in NEGATIVE:
        return -abs(days)
    return Decimal(days)


def project(rows) -> Decimal:
    """Balance from (entry_type, days) pairs, oldest first. Never stored."""
    return sum((signed_days(entry_type, Decimal(str(days))) for entry_type, days in rows),
               ZERO)


def available(balance: Decimal, committed: Decimal) -> Decimal:
    """What is left once the days already committed to pending requests are held."""
    return Decimal(balance) - Decimal(committed)
