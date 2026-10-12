from __future__ import annotations

CL, RH, SCL, EL, COL, VL = "CL", "RH", "SCL", "EL", "COL", "VL"
CATEGORIES = (CL, RH, SCL, EL, COL, VL)
ENTITLEMENT = {CL: 8, RH: 2, SCL: 15, EL: 30, COL: 20, VL: 60}
CARRY_FORWARD = frozenset({EL, COL})
CONTINUOUS = frozenset({EL, COL, VL})
FACULTY_ONLY = frozenset({VL})
NON_FACULTY_ONLY = frozenset({EL})
HALF_DAY_ALLOWED = frozenset({CL})


def is_eligible(category: str, is_faculty: bool) -> bool:
    """Check if the category is eligible based on faculty status (BR-EL-001, BR-EL-005, BR-EL-006)."""
    if category in FACULTY_ONLY and not is_faculty:
        return False
    if category in NON_FACULTY_ONLY and is_faculty:
        return False
    return True
