"""The six leave categories and what the business rules fix about each; numbers live in policy."""
from __future__ import annotations

from dataclasses import dataclass

CL, RH, SCL, EL, COL, VL = "CL", "RH", "SCL", "EL", "COL", "VL"
ALL = (CL, RH, SCL, EL, COL, VL)

LABELS = {
    CL: "Casual Leave", RH: "Restricted Holiday", SCL: "Special Casual Leave",
    EL: "Earned Leave", COL: "Commuted Leave", VL: "Vacation Leave",
}

FACULTY, STAFF = "faculty", "staff"
EMPLOYEE_KINDS = (FACULTY, STAFF)


@dataclass(frozen=True)
class Category:
    code: str
    #: BR-EL-016: the Unit Head decides; otherwise BR-EL-017 recommends.
    unit_head_final: bool
    #: BR-EL-011: every calendar day counts, weekends and closed holidays included.
    continuous: bool
    #: BR-EL-010.
    half_day: bool
    #: BR-EL-002/003/004 lapse; BR-EL-005/009 carry; BR-EL-007 converts.
    year_end: str
    #: BR-EL-005/006: who receives the annual credit.
    credited_to: tuple[str, ...]
    #: BR-EL-001/006/008: who may apply for it.
    availed_by: tuple[str, ...]
    #: BR-EL-025/027: extension and formal resumption.
    extendable: bool


LAPSE, CARRY, CONVERT = "lapse", "carry", "convert"

CATEGORIES: dict[str, Category] = {
    CL: Category(CL, True, False, True, LAPSE, EMPLOYEE_KINDS, EMPLOYEE_KINDS, False),
    RH: Category(RH, True, False, False, LAPSE, EMPLOYEE_KINDS, EMPLOYEE_KINDS, False),
    SCL: Category(SCL, False, False, False, LAPSE, EMPLOYEE_KINDS, EMPLOYEE_KINDS, False),
    EL: Category(EL, False, True, False, CARRY, (STAFF,), EMPLOYEE_KINDS, True),
    COL: Category(COL, False, True, False, CARRY, EMPLOYEE_KINDS, EMPLOYEE_KINDS, True),
    VL: Category(VL, False, True, False, CONVERT, (FACULTY,), (FACULTY,), True),
}

#: BR-EL-007: VL converts into EL at this many VL days per EL day.
VL_PER_EL = 2


def get(code: str) -> Category:
    try:
        return CATEGORIES[code]
    except KeyError:
        raise ValueError(f"{code!r} is not a leave category.") from None


def applicable(code: str, employee_kind: str) -> bool:
    """BR-EL-001: whether this kind of employee may apply for this category."""
    return code in CATEGORIES and employee_kind in CATEGORIES[code].availed_by
