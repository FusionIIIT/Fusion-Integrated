"""Leave categories and eligibility rules (BR-EL-001..009)."""
from __future__ import annotations

CL = "CL"
RH = "RH"
SCL = "SCL"
EL = "EL"
VL = "VL"
COL = "COL"

ALL_CATEGORIES = {CL, RH, SCL, EL, VL, COL}

CONTINUOUS_COUNT_CATEGORIES = {EL, COL, VL}
WORKING_DAY_COUNT_CATEGORIES = {CL, SCL, RH}

ANNUAL_ENTITLEMENTS = {
    CL: 8,
    RH: 2,
    SCL: 15,
    EL: 30,
    VL: 60,
    COL: 20,
}


def is_eligible_for_category(category: str, is_faculty: bool) -> bool:
    """Validate whether employee is eligible for the requested category (BR-EL-001, BR-EL-005, BR-EL-006)."""
    if category not in ALL_CATEGORIES:
        return False
    if category == VL and not is_faculty:
        # Vacation Leave is strictly for faculty
        return False
    return True
