"""Leave categories and their policy attributes (BR-EL-001..011).

The rules are stated once here as data, so a policy change is a row rather than
a hunt through `if` chains. Pure Python: no Django, so this file tests in
milliseconds and a service cannot smuggle a query into a policy decision.

Sources: PS v1.4 §3 (entitlement, applicability, carry-forward) and §4
(leave-day counting), BR-EL-001..011.
"""
from __future__ import annotations

from decimal import Decimal

CL = "cl"
RH = "rh"
SCL = "scl"
EL = "el"
COL = "col"
VL = "vl"

CATEGORIES: tuple[str, ...] = (CL, RH, SCL, EL, COL, VL)

LABELS: dict[str, str] = {
    CL: "Casual Leave",
    RH: "Restricted Holiday",
    SCL: "Special Casual Leave",
    EL: "Earned Leave",
    COL: "Commuted Leave",
    VL: "Vacation Leave",
}

#: BR-EL-002/003/004/005/009/006 and PS §3 entitlements, per leave year.
ENTITLEMENT: dict[str, Decimal] = {
    CL: Decimal("8"),
    RH: Decimal("2"),
    SCL: Decimal("15"),
    EL: Decimal("30"),
    COL: Decimal("20"),
    VL: Decimal("60"),
}

#: BR-EL-011: weekends and closed holidays inside the interval are charged.
CONTINUOUS_COUNTING: frozenset[str] = frozenset({EL, COL, VL})
#: BR-EL-011: the continuous-day rule does not apply to these.
EXCLUDED_FROM_CONTINUOUS: frozenset[str] = frozenset({CL, SCL, RH})

#: BR-EL-010: a half day is a CL concept; an approved half consumes 0.5 day.
HALF_DAY_CATEGORIES: frozenset[str] = frozenset({CL})
HALF_DAY_DAYS = Decimal("0.5")

#: BR-EL-005/009: unused balance survives the year boundary.
CARRY_FORWARD: frozenset[str] = frozenset({EL, COL})
#: BR-EL-002/003/004: unused balance lapses at year end.
LAPSES: frozenset[str] = frozenset({CL, RH, SCL})

#: BR-EL-007/008: all unused faculty VL converts to EL, including fractions.
VL_TO_EL_RATIO = Decimal("2")

#: BR-EL-016: the Unit Head decides. BR-EL-017: everyone else is reviewed then
#: routed on through the configured hierarchy.
UNIT_HEAD_FINAL: frozenset[str] = frozenset({CL, RH})
HIGHER_SANCTION: frozenset[str] = frozenset({SCL, EL, COL, VL})

#: BR-EL-025: extension is available for ongoing EL, COL and VL only.
EXTENDABLE: frozenset[str] = frozenset({EL, COL, VL})
#: BR-EL-027: formal resumption review applies to EL, COL and VL.
RESUMPTION_REVIEWED: frozenset[str] = frozenset({EL, COL, VL})

#: Employee kinds, as the IAM reports them.
FACULTY = "faculty"
STAFF = "staff"
EMPLOYEE_KINDS = (FACULTY, STAFF)

#: BR-EL-006: VL is a faculty entitlement. BR-EL-005: EL is non-faculty.
FACULTY_ONLY: frozenset[str] = frozenset({VL})
NON_FACULTY_ONLY: frozenset[str] = frozenset({EL})

#: BR-EL-013: Station Leave is information inside the application, never its
#: own request. The reason reported most often is being outside Jabalpur.
STATION_LEAVE = "station_leave"


def is_continuous(category: str) -> bool:
    """BR-EL-011 — is every calendar day in the interval a leave day?"""
    return category in CONTINUOUS_COUNTING


def supports_half_day(category: str) -> bool:
    """BR-EL-010 — first-half and second-half requests are a CL feature."""
    return category in HALF_DAY_CATEGORIES


def may_be_used_by(category: str, employee_kind: str) -> bool:
    """BR-EL-001 — category applicability for the employee's kind.

    An unknown kind is refused rather than assumed, because the two categories
    that discriminate (EL, VL) are the two largest entitlements.
    """
    if category not in CATEGORIES:
        return False
    if employee_kind not in EMPLOYEE_KINDS:
        return False
    if category in FACULTY_ONLY:
        return employee_kind == FACULTY
    if category in NON_FACULTY_ONLY:
        return employee_kind != FACULTY
    return True
