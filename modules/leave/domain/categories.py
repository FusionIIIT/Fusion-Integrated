"""The leave-category vocabulary (CFR-EL-002, BR-EL-001) and what structurally separates them."""
from __future__ import annotations

CASUAL = "CL"
RESTRICTED_HOLIDAY = "RH"
SPECIAL_CASUAL = "SCL"
EARNED = "EL"
COMMUTED = "COL"
VACATION = "VL"

CATEGORIES: tuple[str, ...] = (CASUAL, RESTRICTED_HOLIDAY, SPECIAL_CASUAL,
                               EARNED, COMMUTED, VACATION)

#: Counted across weekends and closed holidays inside the interval (BR-EL-011).
CONTINUOUS: frozenset[str] = frozenset({EARNED, COMMUTED, VACATION})

#: CL, SCL and RH exclude weekends and holidays from the count (BR-EL-011).
WORKING_DAY: frozenset[str] = frozenset({CASUAL, RESTRICTED_HOLIDAY, SPECIAL_CASUAL})

#: Only these carry a year-end balance outcome other than lapse (BR-EL-005, BR-EL-009).
CARRIES_FORWARD: frozenset[str] = frozenset({EARNED, COMMUTED})

#: Everything else lapses unused at year end (BR-EL-002, BR-EL-003, BR-EL-004).
LAPSES: frozenset[str] = frozenset({CASUAL, RESTRICTED_HOLIDAY, SPECIAL_CASUAL,
                                    VACATION})

#: The Director's own leave never routes through a Unit Head (BR-EL-020).
SELF_SANCTION_CATEGORY_INDEPENDENT = True

FACULTY = "faculty"
STAFF = "staff"
EMPLOYEE_KINDS: tuple[str, ...] = (FACULTY, STAFF)

#: First-half and second-half CL are distinct slots on one date (BR-EL-010).
FIRST_HALF = "first_half"
SECOND_HALF = "second_half"
HALVES: tuple[str, ...] = (FIRST_HALF, SECOND_HALF)

HALF_DAY_COST = "0.5"


def is_continuous(category: str) -> bool:
    return category in CONTINUOUS


def requires_calendar_date(category: str) -> bool:
    """RH and VL are meaningless without the calendar behind them."""
    return category in (RESTRICTED_HOLIDAY, VACATION)