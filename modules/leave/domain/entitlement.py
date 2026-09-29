"""Annual credit, lapse, carry-forward and year-end conversion."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from enum import StrEnum

from modules.leave.domain.categories import Category

ZERO = Decimal("0")
CENT = Decimal("0.01")


class ConversionRounding(StrEnum):
    #: 5 VL -> 2.5 EL. The remainder is kept.
    EXACT_HALF = "EXACT_HALF"
    #: 5 VL -> 2 EL. The remainder is discarded.
    FLOOR_TO_WHOLE = "FLOOR_TO_WHOLE"
    #: 5 VL -> 3 EL. The remainder is rounded up.
    ROUND_TO_WHOLE = "ROUND_TO_WHOLE"


@dataclass(frozen=True)
class CategoryPolicy:
    """One category's settings under one effective policy version."""

    category: Category
    annual_credit: Decimal
    carries_forward: bool
    carry_forward_cap: Decimal | None = None


@dataclass(frozen=True)
class Balance:
    """What a person holds in one category for one year."""

    category: Category
    opening: Decimal = ZERO
    credited: Decimal = ZERO
    consumed: Decimal = ZERO
    restored: Decimal = ZERO

    @property
    def available(self) -> Decimal:
        return self.opening + self.credited - self.consumed + self.restored


def has_sufficient_balance(balance: Balance, requested: Decimal) -> bool:
    """BR-EL-001 and SRS-EL-007. Checked before submission and before approval."""
    return requested <= balance.available


def carry_forward(policy: CategoryPolicy, closing: Decimal) -> Decimal:
    """What survives into next year for one category. BR-EL-002 to BR-EL-009."""
    if not policy.carries_forward or closing <= ZERO:
        return ZERO
    if policy.carry_forward_cap is None:
        return closing
    return min(closing, policy.carry_forward_cap)


#: BR-EL-008: converted EL is ordinary EL and carries forward with it.
def convert_vl_to_el(
    unused_vl: Decimal,
    ratio: Decimal,
    rounding: ConversionRounding = ConversionRounding.EXACT_HALF,
) -> Decimal:
    """BR-EL-007. Unused vacation leave becomes earned leave at year end."""
    if unused_vl <= ZERO:
        return ZERO
    if ratio <= ZERO:
        raise ValueError("conversion ratio must be positive")
    raw = unused_vl / ratio
    if rounding is ConversionRounding.EXACT_HALF:
        return raw.quantize(CENT)
    if rounding is ConversionRounding.FLOOR_TO_WHOLE:
        return raw.quantize(Decimal("1"), rounding=ROUND_DOWN)
    return raw.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class YearEndOutcome:
    """What the year-end run does to one person's balances. BR-EL-007, SF-EL-001."""

    lapsed: dict[Category, Decimal]
    carried: dict[Category, Decimal]
    converted_vl: Decimal
    el_from_conversion: Decimal


def close_year(
    balances: dict[Category, Balance],
    policies: dict[Category, CategoryPolicy],
    *,
    vl_to_el_ratio: Decimal | None = None,
    rounding: ConversionRounding = ConversionRounding.EXACT_HALF,
) -> YearEndOutcome:
    """Settle every category at year end."""
    lapsed: dict[Category, Decimal] = {}
    carried: dict[Category, Decimal] = {}
    converted_vl = ZERO
    el_from_conversion = ZERO

    vl = balances.get(Category.VL)
    if vl is not None and vl_to_el_ratio is not None and vl.available > ZERO:
        converted_vl = vl.available
        el_from_conversion = convert_vl_to_el(converted_vl, vl_to_el_ratio, rounding)

    for category, balance in balances.items():
        policy = policies.get(category)
        closing = balance.available
        if category is Category.VL:
            carried[category] = ZERO
            lapsed[category] = ZERO if converted_vl else closing
            continue
        if category is Category.EL:
            closing += el_from_conversion
        if policy is None or not policy.carries_forward:
            carried[category] = ZERO
            lapsed[category] = max(closing, ZERO)
            continue
        kept = carry_forward(policy, closing)
        carried[category] = kept
        lapsed[category] = max(closing - kept, ZERO)

    return YearEndOutcome(
        lapsed=lapsed,
        carried=carried,
        converted_vl=converted_vl,
        el_from_conversion=el_from_conversion,
    )
