"""Leave entitlements and year-end disposition (BR-EL-002..006, 009).

Only the figures the specification states outright are encoded here. Where a
rule needs the published holiday/RH calendar or the institute Academic Calendar
(BR-EL-003, BR-EL-006), that source is an input or is deferred, not invented.

The year boundary itself (calendar vs fiscal, and the exact instant) is an open
item in the unresolved register; this module deals in annual amounts only and
does not decide when a year starts or ends.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

CL = "CL"
RH = "RH"
SCL = "SCL"
EL = "EL"
COL = "COL"
VL = "VL"

CATEGORIES = (CL, RH, SCL, EL, COL, VL)

#: BR-EL-002/003/004/009 - fixed annual grant, independent of role.
FIXED_ANNUAL_ENTITLEMENT: dict[str, Decimal] = {
    CL: Decimal("8"),
    RH: Decimal("2"),
    SCL: Decimal("15"),
    COL: Decimal("20"),
}

#: BR-EL-005/006 - role-scoped grants.
NON_FACULTY_EL_PER_YEAR = Decimal("30")
FACULTY_VL_PER_YEAR = Decimal("60")


class Disposition(StrEnum):
    """BR-EL-002/003/004/005/007/009 - what an unused balance becomes."""

    LAPSE = "lapse"
    CARRY = "carry"
    CONVERT = "convert"


def annual_entitlement(category: str, *, is_faculty: bool) -> Decimal:
    """Days credited per year.

    Faculty earn no EL directly (BR-EL-005) and non-faculty earn no VL
    (BR-EL-006): a faculty member's EL accrues only through VL conversion
    (BR-EL-007).
    """
    if category == EL:
        return Decimal("0") if is_faculty else NON_FACULTY_EL_PER_YEAR
    if category == VL:
        return FACULTY_VL_PER_YEAR if is_faculty else Decimal("0")
    return FIXED_ANNUAL_ENTITLEMENT[category]


def year_end_disposition(category: str) -> Disposition:
    """Whether the unused balance lapses, carries, or converts at year end."""
    if category in (EL, COL):
        return Disposition.CARRY
    if category == VL:
        return Disposition.CONVERT
    return Disposition.LAPSE


@dataclass(frozen=True)
class Entitlement:
    category: str
    days: Decimal
    disposition: Disposition

    @property
    def carries_forward(self) -> bool:
        return self.disposition is Disposition.CARRY


def entitlement_for(category: str, *, is_faculty: bool) -> Entitlement:
    return Entitlement(
        category=category,
        days=annual_entitlement(category, is_faculty=is_faculty),
        disposition=year_end_disposition(category),
    )
