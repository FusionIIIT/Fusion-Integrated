"""Year-end leave-account processing (BR-EL-002..BR-EL-009, EL-UC-020).

Pure arithmetic over each account's unused balance, so the policy is testable
without a database and the service only has to write the resulting ledger rows.

    CL / RH / SCL  unused lapses; no carry-forward
    EL / COL       unused carries forward
    VL             unused converts to EL at 2:1, fractions preserved;
                   VL itself never carries forward
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from modules.elm.domain import enums as e

TWO = Decimal("2")


@dataclass(frozen=True)
class YearEndOutcome:
    category: str
    lapsed: Decimal = Decimal("0")
    carried: Decimal = Decimal("0")
    converted_to_el: Decimal = Decimal("0")


def _d(x) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


def compute(*, category: str, balance) -> YearEndOutcome:
    """What happens to `balance` unused days of `category` at year end."""
    bal = _d(balance)
    if bal <= 0:
        return YearEndOutcome(category)

    if category in (e.CL, e.RH, e.SCL):
        return YearEndOutcome(category, lapsed=bal)
    if category in (e.EL, e.COL):
        return YearEndOutcome(category, carried=bal)
    if category == e.VL:
        # 2 VL : 1 EL, fractions retained (BR-EL-007).
        return YearEndOutcome(category, converted_to_el=(bal / TWO))
    # Unknown category: fail safe by lapsing rather than silently carrying.
    return YearEndOutcome(category, lapsed=bal)
