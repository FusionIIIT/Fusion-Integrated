"""Entitlement and year-end account rules from the synchronized ELM baseline."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN


@dataclass(frozen=True)
class YearEndEntry:
    category: str
    amount: Decimal
    kind: str
    explanation: str


def annual_entitlement(category: str, employee_kind: str, policy) -> Decimal:
    """Return configured annual credit for an employee and category."""
    if category == "CL":
        return Decimal(policy.cl_days)
    if category == "RH":
        return Decimal(policy.rh_days)
    if category == "SCL":
        return Decimal(policy.scl_days)
    if category == "EL" and employee_kind == "staff":
        return Decimal(policy.nonfaculty_el_days)
    if category == "VL" and employee_kind == "faculty":
        return Decimal(policy.faculty_vl_days)
    if category == "COL":
        return Decimal(policy.col_days)
    return Decimal("0")


def year_end_entries(*, cl: Decimal, rh: Decimal, scl: Decimal, el: Decimal,
                     col: Decimal, vl: Decimal, employee_kind: str) -> list[YearEndEntry]:
    """Create idempotently-keyable year-end account movements.

    CL/RH/SCL/VL unused amounts lapse. EL and COL carry forward. Faculty VL is
    converted at exactly 2 VL : 1 EL, preserving fractional EL credit.
    """
    entries: list[YearEndEntry] = []
    if el > 0:
        entries.append(YearEndEntry("EL", el, "carry_forward", "Unused EL carried forward"))
    if col > 0:
        entries.append(YearEndEntry("COL", col, "carry_forward", "Unused COL carried forward"))
    if employee_kind == "faculty" and vl > 0:
        converted = (vl / Decimal("2")).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
        if converted:
            entries.append(YearEndEntry("EL", converted, "vl_conversion", "Unused VL converted at 2:1"))
    return entries


def resumption_adjustment(approved_days: Decimal, actual_days: Decimal) -> Decimal:
    """Balance credit/debit on reviewed early or late resumption."""
    return approved_days - actual_days
