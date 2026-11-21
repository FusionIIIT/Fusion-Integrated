"""Leave categories and the fixed numbers of the policy (BR-EL-001..011)."""
from __future__ import annotations

from decimal import Decimal

CL, RH, SCL, EL, COL, VL = "CL", "RH", "SCL", "EL", "COL", "VL"
ALL_TYPES = (CL, RH, SCL, EL, COL, VL)

STAFF, FACULTY = "staff", "faculty"

NO_HALF, FIRST_HALF, SECOND_HALF = "NONE", "FIRST", "SECOND"
HALVES = (FIRST_HALF, SECOND_HALF)

#: Credit per calendar year by employee kind. Faculty EL is not credited:
#: it only ever arrives through VL conversion (BR-EL-005, BR-EL-008).
ANNUAL_CREDIT: dict[str, dict[str, Decimal]] = {
    FACULTY: {CL: Decimal(8), RH: Decimal(2), SCL: Decimal(15), EL: Decimal(0),
              COL: Decimal(20), VL: Decimal(60)},
    STAFF: {CL: Decimal(8), RH: Decimal(2), SCL: Decimal(15), EL: Decimal(30),
            COL: Decimal(20)},
}

#: BR-EL-007: two days of VL make one day of EL.
VL_PER_EL = Decimal(2)

#: BR-EL-016: the Unit Head sanctions these alone.
UNIT_HEAD_FINAL = frozenset({CL, RH})
#: BR-EL-017/018: the Unit Head only recommends; a higher authority decides.
HIGHER_SANCTION = frozenset({SCL, EL, COL, VL})
#: BR-EL-011: weekends and closed holidays inside the interval count.
CONTINUOUS_COUNT = frozenset({EL, COL, VL})
#: BR-EL-002/003/004: unused days vanish at year end.
LAPSES_AT_YEAR_END = frozenset({CL, RH, SCL})
#: BR-EL-005/009: unused days move into next year.
CARRIES_FORWARD = frozenset({EL, COL})
#: BR-EL-025/027/028: only these can be extended or resumed early.
EXTENDABLE = frozenset({EL, COL, VL})
#: BR-EL-009
NEEDS_MEDICAL_EVIDENCE = frozenset({COL})
#: BR-EL-010
HALF_DAY_TYPES = frozenset({CL})


def credit_for(kind: str) -> dict[str, Decimal]:
    """What a person of this kind is credited each year (BR-EL-001)."""
    return ANNUAL_CREDIT.get(kind, {})


def eligible_types(kind: str) -> tuple[str, ...]:
    return tuple(t for t in ALL_TYPES if t in credit_for(kind))
