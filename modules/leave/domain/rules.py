"""Pure domain business rules for Employee Leave Management (ELM).
Following Fusion architecture: Pure Python, NO Django, DRF, or Celery imports.
"""
from datetime import date, timedelta
from typing import List, Dict, Optional, Tuple


LEAVE_CATEGORIES = ("CL", "RH", "SCL", "EL", "COL", "VL")

STATUS_DRAFT = "DRAFT"
STATUS_AWAITING_SUBSTITUTE = "AWAITING_SUBSTITUTE"
STATUS_APPLICANT_ACTION_REQUIRED = "APPLICANT_ACTION_REQUIRED"
STATUS_AWAITING_UNIT_HEAD = "AWAITING_UNIT_HEAD"
STATUS_AWAITING_ESTABLISHMENT = "AWAITING_ESTABLISHMENT"
STATUS_AWAITING_SANCTION = "AWAITING_SANCTION"
STATUS_AWAITING_DIRECTOR = "AWAITING_DIRECTOR"
STATUS_APPROVED = "APPROVED"
STATUS_REJECTED = "REJECTED"
STATUS_WITHDRAWN = "WITHDRAWN"
STATUS_CANCELLED = "CANCELLED"
STATUS_CANCELLATION_PENDING_UH = "CANCELLATION_PENDING_UH"
STATUS_CANCELLATION_PENDING_EST = "CANCELLATION_PENDING_EST"
STATUS_CANCELLATION_PENDING_SANCTION = "CANCELLATION_PENDING_SANCTION"
STATUS_RESUMPTION_PENDING = "RESUMPTION_PENDING"


def is_continuous_leave_category(category: str) -> bool:
    """EL, COL, and VL count intervening weekends and holidays continuously (BR-EL-011)."""
    return category in ("EL", "COL", "VL")


def calculate_chargeable_days(
    category: str,
    start_date: date,
    end_date: date,
    is_half_day: bool = False,
    holidays: Optional[List[date]] = None,
) -> float:
    """Calculate chargeable days based on leave category rules.
    - CL half day = 0.5 (BR-EL-010)
    - CL, RH, SCL exclude closed weekends and holidays (BR-EL-011)
    - EL, COL, VL count all calendar days continuously (BR-EL-010, BR-EL-011)
    """
    if category == "CL" and is_half_day:
        return 0.5

    holidays_set = set(holidays or [])
    current = start_date
    total_days = 0.0

    while current <= end_date:
        if is_continuous_leave_category(category):
            total_days += 1.0
        else:
            # Weekend check (5=Sat, 6=Sun) and holiday check
            is_weekend = current.weekday() in (5, 6)
            is_holiday = current in holidays_set
            if not is_weekend and not is_holiday:
                total_days += 1.0
        current += timedelta(days=1)

    return total_days


def check_leave_overlap(
    new_start: date,
    new_end: date,
    new_is_half_day: bool,
    new_half_type: Optional[str],
    existing_start: date,
    existing_end: date,
    existing_is_half_day: bool,
    existing_half_type: Optional[str],
) -> bool:
    """BR-EL-012: Check overlap with active/approved leave.
    Exception: First-half and second-half CL on same date are non-overlapping.
    """
    if new_end < existing_start or new_start > existing_end:
        return False  # No date overlap

    # Check same-date half-day exception
    if (
        new_start == new_end == existing_start == existing_end
        and new_is_half_day
        and existing_is_half_day
    ):
        if new_half_type and existing_half_type and new_half_type != existing_half_type:
            return False  # Different halves: Allowed!

    return True


def convert_vl_to_el_at_year_end(unused_vl: float) -> Tuple[float, float]:
    """BR-EL-007, BR-EL-008:
    2 VL : 1 EL ratio, fractional conversion allowed.
    VL itself becomes 0. Converted EL is returned.
    """
    converted_el = unused_vl / 2.0
    return 0.0, converted_el


def process_year_end_lapse_and_carry_forward(
    employee_type: str,  # 'faculty' or 'staff'
    balances: Dict[str, float],
) -> Dict[str, float]:
    """BR-EL-002, 003, 004, 005, 007, 008, 009:
    - CL, RH, SCL: Lapse (do not carry forward)
    - Faculty VL: Convert 2 VL -> 1 EL (preserve fractional), VL lapses to 0
    - Non-faculty EL & COL: Carry forward
    """
    new_balances = dict(balances)

    # CL, RH, SCL lapse
    new_balances["CL"] = 0.0
    new_balances["RH"] = 0.0
    new_balances["SCL"] = 0.0

    if employee_type == "faculty":
        unused_vl = new_balances.get("VL", 0.0)
        _, converted_el = convert_vl_to_el_at_year_end(unused_vl)
        new_balances["VL"] = 0.0
        new_balances["EL"] = new_balances.get("EL", 0.0) + converted_el
    else:
        # Non-faculty EL carries forward as is
        pass

    # COL carries forward
    return new_balances


def determine_initial_routing_state(
    category: str,
    applicant_role: str,
    requires_substitute: bool,
) -> str:
    """Determine initial workflow state based on specifications (CW-EL-01, BW-EL-01-09)."""
    if requires_substitute:
        return STATUS_AWAITING_SUBSTITUTE
    if applicant_role == "director":
        return STATUS_AWAITING_DIRECTOR
    return STATUS_AWAITING_UNIT_HEAD


def determine_next_state_after_unit_head(
    category: str,
    recommendation: str,  # 'RECOMMENDED' or 'NOT_RECOMMENDED'
    establishment_configured: bool = False,
) -> str:
    """BR-EL-016, BR-EL-017, BR-EL-019:
    - For CL and RH: Unit Head decision is final (handled separately)
    - For SCL, EL, COL, VL: Unit Head records Recommended/Not Recommended
      Not Recommended is NOT a final rejection. Advances to Establishment or Sanction.
    """
    if establishment_configured:
        return STATUS_AWAITING_ESTABLISHMENT
    return STATUS_AWAITING_SANCTION
