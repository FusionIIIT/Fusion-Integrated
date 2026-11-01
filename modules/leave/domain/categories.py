"""Leave categories and the static rules that hang off them (BR-EL-001..011, 025..028)."""
from __future__ import annotations

CL = "CL"
RH = "RH"
SCL = "SCL"
EL = "EL"
COL = "COL"
VL = "VL"

CATEGORIES: tuple[str, ...] = (CL, RH, SCL, EL, COL, VL)

LABELS = {
    CL: "Casual Leave",
    RH: "Restricted Holiday",
    SCL: "Special Casual Leave",
    EL: "Earned Leave",
    COL: "Commuted Leave",
    VL: "Vacation Leave",
}

#: Annual entitlement in days (BR-EL-002, 003, 004, 005, 006, 009).
ANNUAL_ENTITLEMENT = {CL: 8, RH: 2, SCL: 15, EL: 30, COL: 20, VL: 60}

#: The Unit Head gives the final decision for these (BR-EL-016).
UNIT_HEAD_FINAL = frozenset({CL, RH})

#: These route on to the configured sanctioning authority (BR-EL-017, 018).
HIGHER_SANCTION = frozenset({SCL, EL, COL, VL})

#: Weekends and closed holidays inside the interval count as leave days (BR-EL-011).
CONTINUOUS_COUNTING = frozenset({EL, COL, VL})

#: Only CL supports halves (BR-EL-010).
HALF_DAY_CATEGORIES = frozenset({CL})

#: Unused balance carries into the next year (BR-EL-005, 009).
CARRY_FORWARD = frozenset({EL, COL})

#: Unused balance lapses at year end (BR-EL-002, 003, 004).
LAPSING = frozenset({CL, RH, SCL})

#: VL is the faculty-only category (BR-EL-006).
FACULTY_ONLY = frozenset({VL})

#: 2 VL convert to 1 EL at year end, fraction included (BR-EL-007).
VL_TO_EL_RATIO = 2

#: Formal resumption review applies to these (BR-EL-027).
RESUMPTION_REVIEWED = frozenset({EL, COL, VL})

#: Only an ongoing EL/COL/VL may be extended (BR-EL-025).
EXTENDABLE = frozenset({EL, COL, VL})

#: COL may require medical evidence (BR-EL-009).
EVIDENCE_CATEGORIES = frozenset({COL})


def is_known(category: str) -> bool:
    return category in CATEGORIES


def allows_half_day(category: str) -> bool:
    return category in HALF_DAY_CATEGORIES


def counts_continuously(category: str) -> bool:
    return category in CONTINUOUS_COUNTING


def unit_head_is_final(category: str) -> bool:
    return category in UNIT_HEAD_FINAL


def requires_higher_sanction(category: str) -> bool:
    return category in HIGHER_SANCTION


def carries_forward(category: str) -> bool:
    return category in CARRY_FORWARD


def lapses(category: str) -> bool:
    return category in LAPSING


def is_faculty_only(category: str) -> bool:
    return category in FACULTY_ONLY


def is_resumption_reviewed(category: str) -> bool:
    return category in RESUMPTION_REVIEWED


def is_extendable(category: str) -> bool:
    return category in EXTENDABLE


def needs_evidence(category: str) -> bool:
    return category in EVIDENCE_CATEGORIES


def applicable_to(category: str, *, is_faculty: bool) -> bool:
    """BR-EL-001: VL is faculty-only; every other category is open to all employees."""
    if not is_known(category):
        return False
    if category in FACULTY_ONLY:
        return is_faculty
    return True
