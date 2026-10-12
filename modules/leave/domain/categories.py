"""Leave categories and the policy-shaped facts that belong to each one.

Pure constants and predicates — the shape of the ELM baseline's seven leave
categories (PS §2–4). Everything here is data a rule needs, never a rule
itself; the rules live in the other domain modules and the services.
"""
from __future__ import annotations

CL = "cl"
RH = "rh"
SCL = "scl"
EL = "el"
COL = "col"
VL = "vl"

CATEGORIES: tuple[str, ...] = (CL, RH, SCL, EL, COL, VL)

CATEGORY_LABELS: dict[str, str] = {
    CL: "Casual Leave",
    RH: "Restricted Holiday",
    SCL: "Special Casual Leave",
    EL: "Earned Leave",
    COL: "Commuted Leave",
    VL: "Vacation Leave",
}

#: BR-EL-011: only these count continuously across weekends and closed
#: holidays inside the interval. CL, SCL and RH are counted on working days.
CONTINUOUS_CATEGORIES: frozenset[str] = frozenset({EL, COL, VL})

#: BR-EL-010: only CL supports first-half / second-half requests, and an
#: approved half day consumes 0.5 day.
HALF_DAY_CATEGORIES: frozenset[str] = frozenset({CL})

#: Year-end outcomes (PS §3, BR-EL-002…009). EL and COL carry forward;
#: CL, RH and SCL lapse; faculty VL converts to EL at the policy ratio and
#: itself does not survive the boundary.
CARRY_FORWARD_CATEGORIES: frozenset[str] = frozenset({EL, COL})
LAPSING_CATEGORIES: frozenset[str] = frozenset({CL, RH, SCL})
CONVERTING_CATEGORIES: frozenset[str] = frozenset({VL})

#: BR-EL-025 / CFR-EL-020: extension and resumption (CFR-EL-021) apply only
#: to these categories. CL/RH/SCL have no extension or formal resumption in
#: this baseline.
EXTENDABLE_CATEGORIES: frozenset[str] = frozenset({EL, COL, VL})
RESUMABLE_CATEGORIES: frozenset[str] = frozenset({EL, COL, VL})

#: BR-EL-006: VL is faculty-only and only during Academic Calendar vacation
#: periods. A non-faculty VL request is not merely unusual, it is invalid.
FACULTY_ONLY_CATEGORIES: frozenset[str] = frozenset({VL})

HALF_FIRST = "first"
HALF_SECOND = "second"
HALF_NONE = "none"
HALF_DAY_CHOICES: tuple[str, ...] = (HALF_NONE, HALF_FIRST, HALF_SECOND)


def is_continuous(category: str) -> bool:
    return category in CONTINUOUS_CATEGORIES


def label_for(category: str) -> str:
    return CATEGORY_LABELS.get(category, category)


def half_day_factor(half_day: str, category: str) -> float:
    """0.5 for a half-day CL, 1.0 otherwise (BR-EL-010)."""
    if category in HALF_DAY_CATEGORIES and half_day in (HALF_FIRST, HALF_SECOND):
        return 0.5
    return 1.0
