"""Year-end processing domain rules (Section 13)."""
from dataclasses import dataclass
from decimal import Decimal

from modules.elm.domain.constants import (
    CL,
    COL,
    DEFAULT_ENTITLEMENTS,
    EL,
    LAPSE_AT_YEAR_END,
    RH,
    SCL,
    VL,
)


@dataclass(frozen=True)
class YearEndOutcome:
    category: str
    previous_unused: Decimal
    lapsed: Decimal
    converted_to_el: Decimal
    carried_forward: Decimal
    new_allocated: Decimal
    new_available: Decimal


def compute_year_end_outcomes(
    balances: dict[str, Decimal],
    is_faculty: bool,
) -> list[YearEndOutcome]:
    """Compute year-end leave outcomes (Section 13).

    - Unused CL, RH, SCL lapse.
    - For faculty, unused VL converts to EL at 2 VL : 1 EL (including fractional).
      VL does not carry forward.
    - EL and COL carry forward according to policy.
    """
    outcomes: list[YearEndOutcome] = []

    # 1. Lapse CL, RH, SCL
    for cat in (CL, RH, SCL):
        unused = balances.get(cat, Decimal("0.0"))
        entitlement = DEFAULT_ENTITLEMENTS[cat]
        outcomes.append(
            YearEndOutcome(
                category=cat,
                previous_unused=unused,
                lapsed=unused,
                converted_to_el=Decimal("0.0"),
                carried_forward=Decimal("0.0"),
                new_allocated=entitlement,
                new_available=entitlement,
            )
        )

    # 2. VL (Faculty only)
    vl_unused = balances.get(VL, Decimal("0.0")) if is_faculty else Decimal("0.0")
    converted_el = (vl_unused / Decimal("2.0")) if is_faculty else Decimal("0.0")
    if is_faculty:
        vl_entitlement = DEFAULT_ENTITLEMENTS[VL]
        outcomes.append(
            YearEndOutcome(
                category=VL,
                previous_unused=vl_unused,
                lapsed=Decimal("0.0"),
                converted_to_el=converted_el,
                carried_forward=Decimal("0.0"),
                new_allocated=vl_entitlement,
                new_available=vl_entitlement,
            )
        )

    # 3. EL
    el_unused = balances.get(EL, Decimal("0.0"))
    el_entitlement = Decimal("0.0") if is_faculty else DEFAULT_ENTITLEMENTS[EL]
    el_carried = el_unused + converted_el
    el_total = el_carried + el_entitlement
    outcomes.append(
        YearEndOutcome(
            category=EL,
            previous_unused=el_unused,
            lapsed=Decimal("0.0"),
            converted_to_el=Decimal("0.0"),
            carried_forward=el_carried,
            new_allocated=el_entitlement,
            new_available=el_total,
        )
    )

    # 4. COL
    col_unused = balances.get(COL, Decimal("0.0"))
    col_entitlement = DEFAULT_ENTITLEMENTS[COL]
    col_carried = col_unused
    col_total = col_carried + col_entitlement
    outcomes.append(
        YearEndOutcome(
            category=COL,
            previous_unused=col_unused,
            lapsed=Decimal("0.0"),
            converted_to_el=Decimal("0.0"),
            carried_forward=col_carried,
            new_allocated=col_entitlement,
            new_available=col_total,
        )
    )

    return outcomes
