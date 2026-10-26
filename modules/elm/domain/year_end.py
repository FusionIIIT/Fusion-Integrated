"""Year-end processing calculation logic.

Pure Python — no Django imports allowed in domain/.
Enforces:
- BR-EL-002: CL lapse
- BR-EL-003: RH lapse
- BR-EL-004: SCL lapse
- BR-EL-005: EL carry forward
- BR-EL-007: Faculty VL-to-EL conversion at 2 VL : 1 EL (including fractions) and VL lapse
- BR-EL-008: Converted EL credited to EL balance and usable
- BR-EL-009: COL carry forward
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from modules.elm.domain.constants import LeaveCategory


@dataclass(frozen=True)
class YearEndAccountInput:
    category: str
    balance: Decimal
    is_faculty: bool = False
    user_id: int | None = None
    user_kind: str | None = None


@dataclass(frozen=True)
class YearEndOutcome:
    category: str
    lapsed_amount: Decimal
    carried_forward_amount: Decimal
    converted_to_el_amount: Decimal  # VL converted to EL

    @property
    def carry_forward_amount(self) -> Decimal:
        return self.carried_forward_amount

    @property
    def converted_to_el(self) -> Decimal:
        return self.converted_to_el_amount


def calculate_year_end_outcome(account: YearEndAccountInput) -> YearEndOutcome:
    """Calculate the year-end disposition of a single leave account.

    Returns YearEndOutcome with exact amounts for lapse, carry-forward, and conversion.
    """
    cat = LeaveCategory(account.category)
    bal = max(Decimal("0.00"), account.balance)

    if cat in (LeaveCategory.CL, LeaveCategory.RH, LeaveCategory.SCL):
        # BR-EL-002, 003, 004: CL, RH, SCL lapse completely at year end
        return YearEndOutcome(
            category=cat.value,
            lapsed_amount=bal,
            carried_forward_amount=Decimal("0.00"),
            converted_to_el_amount=Decimal("0.00"),
        )

    if cat == LeaveCategory.VL:
        # BR-EL-007: At year end, unused faculty VL converts to EL at 2 VL : 1 EL
        # (including fractional conversion). VL itself does NOT carry forward.
        converted_el = bal / Decimal("2")
        return YearEndOutcome(
            category=cat.value,
            lapsed_amount=bal,  # VL itself lapses from the VL account
            carried_forward_amount=Decimal("0.00"),
            converted_to_el_amount=converted_el,
        )

    if cat in (LeaveCategory.EL, LeaveCategory.COL):
        # BR-EL-005, 009: EL and COL carry forward
        return YearEndOutcome(
            category=cat.value,
            lapsed_amount=Decimal("0.00"),
            carried_forward_amount=bal,
            converted_to_el_amount=Decimal("0.00"),
        )

    return YearEndOutcome(
        category=account.category,
        lapsed_amount=Decimal("0.00"),
        carried_forward_amount=bal,
        converted_to_el_amount=Decimal("0.00"),
    )
