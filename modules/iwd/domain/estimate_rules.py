from decimal import Decimal
from typing import Tuple
from .models import Role, CostBand, determine_cost_band

def can_approve_estimate(
    role: str,
    total_cost: Decimal,
    committee_reviewed: bool,
    forwarded_to_director: bool
) -> Tuple[bool, str]:
    band = determine_cost_band(total_cost)

    if band == CostBand.LOW:
        if role in [Role.IWD_ADMIN, "admin"]:
            return True, "IWD Admin low-cost internal approval authorized."
        return False, "Low-cost estimates require IWD Admin approval."

    elif band == CostBand.MID:
        if not committee_reviewed:
            return False, "Mid-range estimates require Review Committee necessity/feasibility review first."
        if forwarded_to_director:
            if role in [Role.DIRECTOR, "director"]:
                return True, "Director approval for forwarded mid-range estimate authorized."
            return False, "Forwarded mid-range estimate must be approved by Director."
        if role in [Role.DEPARTMENT_HEAD, "hod"]:
            return True, "Department Head mid-range approval authorized."
        return False, "Mid-range estimates require Department Head approval."

    elif band == CostBand.HIGH:
        if role in [Role.DIRECTOR, "director"]:
            return True, "Director high-cost approval authorized."
        return False, "High-cost estimates (> Rs. 2.5 Lakh) strictly require Director approval."

    return False, "Unknown cost band or role authorization failure."

def validate_rejection(reason: str) -> Tuple[bool, str]:
    if not reason or not reason.strip():
        return False, "Rejection reason is mandatory."
    return True, "Valid rejection reason."
