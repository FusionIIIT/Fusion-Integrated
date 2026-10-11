"""Year-end leave-account outcomes (BR-EL-002..009, EL-UC-020).

Entering the year boundary applies one of three outcomes per category:

    lapse          unused CL, RH and SCL do not carry forward
    carry_forward  unused EL and COL survive, according to policy
    convert        all unused faculty VL becomes EL at 2 VL : 1 EL, including
                   fractions, and no VL carries forward (BR-EL-007/008)

Pure Python, and Decimal throughout: an odd VL balance must convert to the
corresponding fractional EL rather than rounding to something the employee did
not have.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from modules.leave.domain import categories as cat

LAPSE = "lapse"
CARRY_FORWARD = "carry_forward"
CONVERT = "convert"

CENTS = Decimal("0.01")


@dataclass(frozen=True)
class YearEndOutcome:
    category: str
    action: str
    days_in: Decimal
    days_out: Decimal
    into_category: str = ""

    @property
    def is_noop(self) -> bool:
        return self.days_in == 0 and self.days_out == 0


def outcome_for(category: str, available: Decimal, *,
                vl_to_el_ratio: Decimal = cat.VL_TO_EL_RATIO) -> YearEndOutcome:
    """What the year boundary does to one account's unused balance."""
    available = max(Decimal("0"), available)
    if category in cat.LAPSES:
        return YearEndOutcome(category, LAPSE, available, Decimal("0"))
    if category in cat.CARRY_FORWARD:
        return YearEndOutcome(category, CARRY_FORWARD, available, available)
    if category == cat.VL:
        if vl_to_el_ratio <= 0:
            raise ValueError("VL to EL ratio must be positive.")
        converted = (available / vl_to_el_ratio).quantize(CENTS,
                                                          rounding=ROUND_HALF_UP)
        return YearEndOutcome(category, CONVERT, available, converted,
                             into_category=cat.EL)
    # An unrecognised category is reported, never guessed at: silently lapsing
    # a balance nobody modelled is how an employee loses days they had.
    return YearEndOutcome(category, LAPSE, available, Decimal("0"))


def vl_to_el(vl_days: Decimal,
             *, ratio: Decimal = cat.VL_TO_EL_RATIO) -> Decimal:
    """BR-EL-007 — 2 VL : 1 EL, fractions preserved."""
    return (max(Decimal("0"), vl_days) / ratio).quantize(CENTS,
                                                         rounding=ROUND_HALF_UP)
