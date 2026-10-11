"""Append-only leave-account arithmetic (SRS-EL-087, SF-EL-001, BR-EL-002..009).

Balances are sums of entries. A correction is a reversing row, never an edit.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from modules.leave.domain.categories import CARRY_FORWARD, CL, COL, EL, LAPSE_AT_YEAR_END, RH, SCL, VL
from modules.leave.domain.eligibility import PolicySnapshot

CREDIT = "credit"
DEBIT = "debit"
LAPSE = "lapse"
CONVERSION = "conversion"
CARRY = "carry_forward"
RESTORATION = "restoration"
REVERSAL = "reversal"
OFFLINE = "offline"

TWOPLACES = Decimal("0.01")


def quantize(value: Decimal) -> Decimal:
    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def running_balance(rows: list[tuple[str, int, Decimal]], category: str,
                    year: int) -> Decimal:
    """`rows` are (category, year, signed amount). EL/COL sum across years."""
    total = Decimal("0")
    for cat, yr, amount in rows:
        if cat != category:
            continue
        if category in CARRY_FORWARD or category == EL:
            total += amount
        elif yr == year:
            total += amount
        elif category == VL and yr == year:
            total += amount
    if category == VL:
        total = Decimal("0")
        for cat, yr, amount in rows:
            if cat == VL and yr == year:
                total += amount
    return total


def annual_credit(kind: str, category: str, policy: PolicySnapshot) -> Decimal:
    if category == CL:
        return policy.cl_annual
    if category == RH:
        return policy.rh_annual
    if category == SCL:
        return policy.scl_annual
    if category == COL:
        return policy.col_annual
    if category == EL and kind != "faculty":
        return policy.el_staff_annual
    if category == VL and kind == "faculty":
        return policy.vl_faculty
    return Decimal("0")


def convert_vl_to_el(unused_vl: Decimal, policy: PolicySnapshot) -> Decimal:
    """BR-EL-007: 2 VL : 1 EL, fractional conversion permitted."""
    num, den = policy.vl_to_el_ratio
    if unused_vl <= 0:
        return Decimal("0")
    return quantize(unused_vl * Decimal(den) / Decimal(num))


def year_end_entries(*, kind: str, year: int, balances: dict[str, Decimal],
                     policy: PolicySnapshot) -> list[tuple[str, str, Decimal, str]]:
    """Return (category, entry_type, signed_amount, memo) for SF-EL-001."""
    out: list[tuple[str, str, Decimal, str]] = []
    for cat in (CL, RH, SCL):
        unused = balances.get(cat, Decimal("0"))
        if unused > 0:
            out.append((cat, LAPSE, -unused, f"Year-end lapse of unused {cat}"))
    if kind == "faculty":
        unused_vl = balances.get(VL, Decimal("0"))
        if unused_vl > 0:
            el_credit = convert_vl_to_el(unused_vl, policy)
            out.append((VL, LAPSE, -unused_vl, "Year-end VL does not carry forward"))
            if el_credit > 0:
                out.append((EL, CONVERSION, el_credit,
                            "Faculty VL converted to EL at 2:1"))
    next_year = year + 1
    for cat in (CL, RH, SCL, COL, EL, VL):
        credit = annual_credit(kind, cat, policy)
        if credit > 0:
            out.append((cat, CREDIT, credit,
                        f"Annual {cat} credit for {next_year}"))
    return out
