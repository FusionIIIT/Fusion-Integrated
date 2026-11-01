"""Domain business rules and policies for IWD."""
from decimal import Decimal
from typing import Tuple


LOW_COST_THRESHOLD = Decimal("25000.00")
MID_RANGE_THRESHOLD = Decimal("250000.00")


class CostBand:
    LOW = "LOW"            # < 25,000
    MID = "MID"            # 25,000 <= total <= 2,50,000
    HIGH = "HIGH"          # > 2,50,000


def determine_cost_band(total_amount: Decimal) -> str:
    """Determine cost band based on total amount per BR-IWD-003.

    - Low: total < Rs.25,000
    - Mid: Rs.25,000 <= total <= Rs.2.5 lakh
    - High: total > Rs.2.5 lakh
    """
    total = Decimal(str(total_amount))
    if total < LOW_COST_THRESHOLD:
        return CostBand.LOW
    elif total <= MID_RANGE_THRESHOLD:
        return CostBand.MID
    else:
        return CostBand.HIGH


def validate_urgent_flag(is_urgent: bool, cost_band: str) -> dict:
    """Validate urgent fast-track routing per BR-IWD-012.

    Urgent status does not waive statutory cost-band thresholds.
    """
    return {
        "is_urgent": is_urgent,
        "cost_band": cost_band,
        "fast_track": is_urgent,
        "preserves_cost_controls": True,
    }


def validate_role_separation(user_role: str, target_role: str) -> bool:
    """BR-IWD-001 & BR-IWD-018: Department Head and Dean are distinct approval roles."""
    if user_role == "DEAN" and target_role == "DEPARTMENT_HEAD":
        return False
    if user_role == "DEPARTMENT_HEAD" and target_role == "DEAN":
        return False
    return user_role == target_role


def can_initiate_procurement(stock_available: bool) -> bool:
    """BR-IWD-010: Stock availability is checked before procurement is initiated."""
    return not stock_available


def can_resolve_complaint(verification_passed: bool) -> bool:
    """BR-IWD-014: Complaint may be marked resolved only after passing physical verification."""
    return bool(verification_passed)


def can_proceed_to_settlement(auditor_validated: bool, director_approved: bool) -> bool:
    """BR-IWD-016: Payment settlement proceeds only after Auditor validation and Director final approval."""
    return bool(auditor_validated and director_approved)

