"""Domain logic for year-end leave processing (EL-UC-020 / EVT-01).

Pure Python — no framework imports.
Enforces BR-EL-002, BR-EL-003, BR-EL-004, BR-EL-005, BR-EL-007, BR-EL-008, BR-EL-009.
"""

from dataclasses import dataclass
from decimal import Decimal

from modules.leave.domain.constants import LeaveCategory, LedgerTransactionType


@dataclass(frozen=True)
class YearEndAdjustment:
    category: str
    delta_days: Decimal
    transaction_type: LedgerTransactionType
    reason: str


def compute_year_end_adjustments(
    employee_kind: str,
    current_balances: dict[str, Decimal],
    vl_to_el_ratio: Decimal = Decimal("2.0"),
    max_el_carry_forward: Decimal = Decimal("300.0"),
) -> list[YearEndAdjustment]:
    """Computes all ledger adjustments required at the year-end boundary.

    BR-EL-002: Lapses unused CL.
    BR-EL-003: Lapses unused RH.
    BR-EL-004: Lapses unused SCL.
    BR-EL-007: Converts unused faculty VL to EL at ratio (default 2:1) including fractional days.
    BR-EL-008: Credits converted EL to EL balance.
    BR-EL-005: Caps EL carry-forward at max_el_carry_forward if applicable.
    """
    adjustments: list[YearEndAdjustment] = []

    # 1. Lapse unused CL
    cl_bal = current_balances.get(LeaveCategory.CL, Decimal("0.0"))
    if cl_bal > Decimal("0.0"):
        adjustments.append(
            YearEndAdjustment(
                category=LeaveCategory.CL,
                delta_days=-cl_bal,
                transaction_type=LedgerTransactionType.LAPSE,
                reason="Year-end lapse of unused Casual Leave (BR-EL-002)",
            )
        )

    # 2. Lapse unused RH
    rh_bal = current_balances.get(LeaveCategory.RH, Decimal("0.0"))
    if rh_bal > Decimal("0.0"):
        adjustments.append(
            YearEndAdjustment(
                category=LeaveCategory.RH,
                delta_days=-rh_bal,
                transaction_type=LedgerTransactionType.LAPSE,
                reason="Year-end lapse of unused Restricted Holiday (BR-EL-003)",
            )
        )

    # 3. Lapse unused SCL
    scl_bal = current_balances.get(LeaveCategory.SCL, Decimal("0.0"))
    if scl_bal > Decimal("0.0"):
        adjustments.append(
            YearEndAdjustment(
                category=LeaveCategory.SCL,
                delta_days=-scl_bal,
                transaction_type=LedgerTransactionType.LAPSE,
                reason="Year-end lapse of unused Special Casual Leave (BR-EL-004)",
            )
        )

    # 4. Faculty VL conversion to EL (BR-EL-007, BR-EL-008)
    if employee_kind == "faculty":
        vl_bal = current_balances.get(LeaveCategory.VL, Decimal("0.0"))
        if vl_bal > Decimal("0.0"):
            # Deduct all remaining VL
            adjustments.append(
                YearEndAdjustment(
                    category=LeaveCategory.VL,
                    delta_days=-vl_bal,
                    transaction_type=LedgerTransactionType.CONVERSION,
                    reason="Year-end conversion of unused VL to EL (BR-EL-007)",
                )
            )
            # Credit converted EL (ratio 2:1 -> divide by 2)
            converted_el = vl_bal / vl_to_el_ratio
            adjustments.append(
                YearEndAdjustment(
                    category=LeaveCategory.EL,
                    delta_days=converted_el,
                    transaction_type=LedgerTransactionType.CONVERSION,
                    reason=(
                        f"Converted {vl_bal} VL to {converted_el} EL at ratio "
                        f"{vl_to_el_ratio}:1 (BR-EL-008)"
                    ),
                )
            )

    # 5. Cap EL carry-forward if exceeding max limit (BR-EL-005)
    el_bal = current_balances.get(LeaveCategory.EL, Decimal("0.0"))
    # Include any converted EL from this run
    if employee_kind == "faculty" and current_balances.get(
        LeaveCategory.VL, Decimal("0.0")
    ) > Decimal("0.0"):
        el_bal += current_balances.get(LeaveCategory.VL, Decimal("0.0")) / vl_to_el_ratio

    if el_bal > max_el_carry_forward:
        excess = el_bal - max_el_carry_forward
        adjustments.append(
            YearEndAdjustment(
                category=LeaveCategory.EL,
                delta_days=-excess,
                transaction_type=LedgerTransactionType.LAPSE,
                reason=(
                    f"EL balance capped at maximum carry-forward of "
                    f"{max_el_carry_forward} days (BR-EL-005)"
                ),
            )
        )

    return adjustments
