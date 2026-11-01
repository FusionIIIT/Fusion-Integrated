"""Year-end leave-account outcomes (BR-EL-002..009, CFR-EL-028, EL-UC-020).

Pure arithmetic over the closing balance, so the run can be replayed against a
year that was already processed and produce exactly the same moves.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from modules.leave.domain import categories as cat
from modules.leave.domain import ledger as led

ZERO = Decimal("0")


@dataclass(frozen=True)
class YearEndOutcome:
    """What year end does to one account: lapse, carry, or convert."""

    category: str
    closing: Decimal
    lapsed: Decimal = ZERO
    carried_forward: Decimal = ZERO
    converted_el: Decimal = ZERO

    def moves(self) -> list[tuple[str, Decimal]]:
        """The ledger rows this outcome writes, in order."""
        rows: list[tuple[str, Decimal]] = []
        if self.lapsed:
            rows.append((led.LAPSE, self.lapsed))
        if self.converted_el:
            rows.append((led.CONVERSION_OUT, self.closing))
            rows.append((led.CONVERSION_IN, self.converted_el))
        if self.carried_forward:
            rows.append((led.CONVERSION_IN, self.carried_forward))
        return rows


def settle(*, category: str, closing: Decimal) -> YearEndOutcome:
    """One account's year-end outcome.

    VL never carries as VL: every unused day converts at 2 VL : 1 EL, fractions
    included (BR-EL-007), and the result is usable EL (BR-EL-008).
    """
    closing = Decimal(closing)
    if closing <= ZERO:
        return YearEndOutcome(category=category, closing=closing)

    if category == cat.VL:
        return YearEndOutcome(category=category, closing=closing,
                              converted_el=closing / cat.VL_TO_EL_RATIO)

    if cat.lapses(category):
        return YearEndOutcome(category=category, closing=closing, lapsed=closing)

    if cat.carries_forward(category):
        return YearEndOutcome(category=category, closing=closing,
                              carried_forward=closing)

    return YearEndOutcome(category=category, closing=closing)


def opening_balance(*, category: str, carried_forward: Decimal) -> Decimal:
    """Next year's opening, plus the annual credit where the category has one."""
    credit = Decimal(cat.ANNUAL_ENTITLEMENT.get(category, 0))
    if category == cat.VL:
        credit = Decimal(cat.ANNUAL_ENTITLEMENT[cat.VL])
    return Decimal(carried_forward) + credit
