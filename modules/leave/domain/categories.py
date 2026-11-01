"""Leave categories and the fixed traits the spec gives each (BR-EL-001..011)."""
from __future__ import annotations

from decimal import Decimal
from enum import StrEnum


class Category(StrEnum):
    CL = "CL"
    RH = "RH"
    SCL = "SCL"
    EL = "EL"
    COL = "COL"
    VL = "VL"


class EmployeeKind(StrEnum):
    FACULTY = "faculty"
    STAFF = "staff"


LABELS = {
    Category.CL: "Casual Leave", Category.RH: "Restricted Holiday",
    Category.SCL: "Special Casual Leave", Category.EL: "Earned Leave",
    Category.COL: "Commuted Leave", Category.VL: "Vacation Leave",
}

# BR-EL-016: the Unit Head decides these finally.
UNIT_HEAD_FINAL = frozenset({Category.CL, Category.RH})
# BR-EL-017/018: the Unit Head only recommends these.
HIGHER_SANCTION = frozenset({Category.SCL, Category.EL, Category.COL, Category.VL})
# BR-EL-011: weekends and closed holidays inside the interval count.
CONTINUOUS_COUNT = frozenset({Category.EL, Category.COL, Category.VL})
# BR-EL-025 and BR-EL-027.
EXTENDABLE = CONTINUOUS_COUNT
RESUMABLE = CONTINUOUS_COUNT
# BR-EL-002..004 lapse; BR-EL-005/009 carry forward.
LAPSES = frozenset({Category.CL, Category.RH, Category.SCL})
CARRIES_FORWARD = frozenset({Category.EL, Category.COL})

DEFAULT_ANNUAL_DAYS = {
    Category.CL: Decimal(8), Category.RH: Decimal(2), Category.SCL: Decimal(15),
    Category.EL: Decimal(30), Category.COL: Decimal(20), Category.VL: Decimal(60),
}


class IneligibleCategory(ValueError):
    pass


def parse_kind(kind: str) -> EmployeeKind:
    try:
        return EmployeeKind(kind)
    except ValueError as exc:
        raise IneligibleCategory(
            "Leave is available to faculty and staff only.") from exc


def check_eligible(category: Category, kind: EmployeeKind) -> None:
    """BR-EL-001 with BR-EL-006: VL belongs to faculty alone."""
    if category is Category.VL and kind is not EmployeeKind.FACULTY:
        raise IneligibleCategory("Vacation Leave is available to faculty only.")


def annual_credit(category: Category, kind: EmployeeKind, configured: Decimal) -> Decimal:
    """BR-EL-005: faculty get no direct EL credit; their EL comes from VL (BR-EL-008)."""
    if category is Category.EL and kind is EmployeeKind.FACULTY:
        return Decimal(0)
    if category is Category.VL and kind is not EmployeeKind.FACULTY:
        return Decimal(0)
    return configured
