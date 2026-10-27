# modules/leave/domain/categories.py

CL = "CL"
RH = "RH"
SCL = "SCL"
EL = "EL"
VL = "VL"
COL = "COL"

ALL_CATEGORIES = {CL, RH, SCL, EL, VL, COL}
CONTINUOUS_COUNT_CATEGORIES = {EL, COL, VL}
WORKING_DAY_CATEGORIES = {CL, SCL, RH}
LAPSE_CATEGORIES = {CL, RH, SCL}
CARRY_FORWARD_CATEGORIES = {EL, COL}

def is_eligible_for_category(category: str, is_faculty: bool) -> bool:
    is_fac = is_faculty is True or str(is_faculty).lower() in ("faculty", "true", "1")
    if category == VL:
        return is_fac
    elif category == EL:
        return True  # non-faculty gets EL, faculty can avail converted EL
    elif category in {CL, RH, SCL, COL}:
        return True
    return False

def get_annual_entitlement(category: str, is_faculty: bool) -> float:
    is_fac = is_faculty is True or str(is_faculty).lower() in ("faculty", "true", "1")
    if category == CL:
        return 8.0
    elif category == RH:
        return 2.0
    elif category == SCL:
        return 15.0
    elif category == EL and not is_fac:
        return 30.0
    elif category == VL and is_fac:
        return 60.0
    elif category == COL:
        return 20.0
    return 0.0
