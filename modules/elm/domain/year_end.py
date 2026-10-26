"""Year-end leave processing rules for ELM.

Pure Python: no Django dependencies.
Enforces:
- BR-EL-002: CL lapse
- BR-EL-003: RH lapse
- BR-EL-004: SCL lapse
- BR-EL-005: EL carry-forward
- BR-EL-007: Faculty VL-to-EL 2:1 conversion (including fractions)
- BR-EL-008: Converted EL credited to EL balance and carried forward
- BR-EL-009: COL carry-forward
"""
from __future__ import annotations

from dataclasses import dataclass

from modules.elm.domain.constants import ANNUAL_ENTITLEMENTS, LeaveCategory


@dataclass(frozen=True)
class CurrentBalanceSnapshot:
    leave_type_code: str
    year: int
    allotted: float
    used: float


@dataclass(frozen=True)
class YearEndOutcome:
    leave_type_code: str
    old_year: int
    new_year: int
    unused_amount: float
    carried_forward: float
    lapsed_amount: float
    converted_amount: float
    new_allotted: float


def compute_year_end_for_employee(
    balances: list[CurrentBalanceSnapshot],
    is_faculty: bool,
    old_year: int,
    new_year: int,
) -> list[YearEndOutcome]:
    """Calculate year-end closing balances, lapse amounts, conversions, and next year opening credits."""
    results: list[YearEndOutcome] = []
    bal_map = {b.leave_type_code: b for b in balances}

    # 1. First compute VL conversion if employee is faculty (BR-EL-007)
    vl_converted_to_el = 0.0
    if is_faculty and LeaveCategory.VL.value in bal_map:
        vl_bal = bal_map[LeaveCategory.VL.value]
        vl_unused = max(0.0, vl_bal.allotted - vl_bal.used)
        # Convert at 2 VL : 1 EL (including fractional conversion)
        vl_converted_to_el = round(vl_unused / 2.0, 2)
        # VL itself does NOT carry forward
        results.append(
            YearEndOutcome(
                leave_type_code=LeaveCategory.VL.value,
                old_year=old_year,
                new_year=new_year,
                unused_amount=vl_unused,
                carried_forward=0.0,
                lapsed_amount=0.0,  # it was converted, not lost
                converted_amount=vl_converted_to_el,
                new_allotted=ANNUAL_ENTITLEMENTS[LeaveCategory.VL],
            )
        )

    # 2. Process CL (BR-EL-002: lapse, no carry forward)
    if LeaveCategory.CL.value in bal_map:
        cl_bal = bal_map[LeaveCategory.CL.value]
        cl_unused = max(0.0, cl_bal.allotted - cl_bal.used)
        results.append(
            YearEndOutcome(
                leave_type_code=LeaveCategory.CL.value,
                old_year=old_year,
                new_year=new_year,
                unused_amount=cl_unused,
                carried_forward=0.0,
                lapsed_amount=cl_unused,
                converted_amount=0.0,
                new_allotted=ANNUAL_ENTITLEMENTS[LeaveCategory.CL],
            )
        )

    # 3. Process RH (BR-EL-003: lapse, no carry forward)
    if LeaveCategory.RH.value in bal_map:
        rh_bal = bal_map[LeaveCategory.RH.value]
        rh_unused = max(0.0, rh_bal.allotted - rh_bal.used)
        results.append(
            YearEndOutcome(
                leave_type_code=LeaveCategory.RH.value,
                old_year=old_year,
                new_year=new_year,
                unused_amount=rh_unused,
                carried_forward=0.0,
                lapsed_amount=rh_unused,
                converted_amount=0.0,
                new_allotted=ANNUAL_ENTITLEMENTS[LeaveCategory.RH],
            )
        )

    # 4. Process SCL (BR-EL-004: lapse, no carry forward)
    if LeaveCategory.SCL.value in bal_map:
        scl_bal = bal_map[LeaveCategory.SCL.value]
        scl_unused = max(0.0, scl_bal.allotted - scl_bal.used)
        results.append(
            YearEndOutcome(
                leave_type_code=LeaveCategory.SCL.value,
                old_year=old_year,
                new_year=new_year,
                unused_amount=scl_unused,
                carried_forward=0.0,
                lapsed_amount=scl_unused,
                converted_amount=0.0,
                new_allotted=ANNUAL_ENTITLEMENTS[LeaveCategory.SCL],
            )
        )

    # 5. Process EL (BR-EL-005, BR-EL-008: carry forward + converted EL from VL + new credit)
    el_unused = 0.0
    if LeaveCategory.EL.value in bal_map:
        el_bal = bal_map[LeaveCategory.EL.value]
        el_unused = max(0.0, el_bal.allotted - el_bal.used)

    # Base annual credit: non-faculty gets 30 days directly; faculty gets converted EL
    base_annual_credit = 0.0 if is_faculty else ANNUAL_ENTITLEMENTS[LeaveCategory.EL]
    new_el_allotted = round(el_unused + base_annual_credit + vl_converted_to_el, 2)

    results.append(
        YearEndOutcome(
            leave_type_code=LeaveCategory.EL.value,
            old_year=old_year,
            new_year=new_year,
            unused_amount=el_unused,
            carried_forward=el_unused,
            lapsed_amount=0.0,
            converted_amount=vl_converted_to_el,
            new_allotted=new_el_allotted,
        )
    )

    # 6. Process COL (BR-EL-009: carry forward + 20 new credit)
    if LeaveCategory.COL.value in bal_map:
        col_bal = bal_map[LeaveCategory.COL.value]
        col_unused = max(0.0, col_bal.allotted - col_bal.used)
        results.append(
            YearEndOutcome(
                leave_type_code=LeaveCategory.COL.value,
                old_year=old_year,
                new_year=new_year,
                unused_amount=col_unused,
                carried_forward=col_unused,
                lapsed_amount=0.0,
                converted_amount=0.0,
                new_allotted=round(col_unused + ANNUAL_ENTITLEMENTS[LeaveCategory.COL], 2),
            )
        )

    return results
