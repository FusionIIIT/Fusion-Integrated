"""Business rules for Employee Leave Management (ELM).

Pure Python — no Django, DRF or Celery imports permitted.
Implements BR-EL-001 through BR-EL-038.
"""
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple

from modules.leave.domain.calculator import calculate_leave_days
from modules.leave.domain.constants import (
    HalfDayOption,
    LeaveCategory,
    ResumptionOutcome,
)


def validate_leave_application(
    category: str | LeaveCategory,
    start_date: date,
    end_date: date,
    available_balance: Decimal,
    computed_days: Decimal,
    employee_kind: str,
    half_day: Optional[str | HalfDayOption] = None,
    valid_rh_dates: Optional[Set[date]] = None,
    vacation_periods: Optional[List[Tuple[date, date]]] = None,
    has_medical_certificate: bool = False,
) -> None:
    """Validate a leave application against institute rules.

    BR-EL-001: Category eligibility
    BR-EL-003: RH calendar applicability
    BR-EL-006: Faculty VL vacation-period applicability
    BR-EL-009: Commuted Leave (COL) medical validation
    BR-EL-010: Half-day CL validation
    """
    cat = LeaveCategory(category)
    half = HalfDayOption(half_day) if half_day else HalfDayOption.NONE

    # Category eligibility
    if cat == LeaveCategory.VL and employee_kind != "faculty":
        raise ValueError("Vacation Leave (VL) is only available to faculty employees.")

    # Dates
    if start_date > end_date:
        raise ValueError("Leave start date cannot be after end date.")

    # Balance check
    if computed_days > available_balance:
        raise ValueError(
            f"Insufficient leave balance for {cat.value}: requested {computed_days} day(s), "
            f"but available balance is {available_balance} day(s)."
        )

    # RH validation (BR-EL-003, BR-EL-031)
    if cat == LeaveCategory.RH:
        if start_date != end_date:
            raise ValueError("Restricted Holiday (RH) must be requested for a single day.")
        rh_set = valid_rh_dates or set()
        if start_date not in rh_set:
            raise ValueError(
                f"Selected date {start_date} is not an applicable Restricted Holiday in the published calendar."
            )

    # VL vacation period validation (BR-EL-006)
    if cat == LeaveCategory.VL:
        periods = vacation_periods or []
        inside_vacation = any(p_start <= start_date and end_date <= p_end for p_start, p_end in periods)
        if not inside_vacation:
            raise ValueError(
                f"Vacation Leave ({start_date} to {end_date}) must fall entirely within a published Academic Calendar vacation period."
            )

    # COL medical evidence (BR-EL-009)
    if cat == LeaveCategory.COL and not has_medical_certificate:
        raise ValueError("Commuted Leave (COL) requires supporting medical certificate.")


def check_leave_overlap(
    existing_leaves: List[Dict[str, Any]],
    new_start: date,
    new_end: date,
    new_category: str | LeaveCategory,
    new_half_day: Optional[str | HalfDayOption] = None,
) -> None:
    """Validate applicant non-overlap with half-day CL exception (BR-EL-012).

    A new request shall not impermissibly overlap the employee's active pending or
    approved leave; first-half and second-half CL on the same date are non-overlapping.
    """
    new_cat = LeaveCategory(new_category)
    new_half = HalfDayOption(new_half_day) if new_half_day else HalfDayOption.NONE

    for leave in existing_leaves:
        # Check active statuses: exclude terminal non-active (REJECTED, WITHDRAWN, CANCELLED)
        status = leave.get("status")
        if status in ("REJECTED", "WITHDRAWN", "CANCELLED"):
            continue

        ex_start = leave["start_date"]
        ex_end = leave["end_date"]
        ex_cat = LeaveCategory(leave.get("category", "CL"))
        ex_half = HalfDayOption(leave.get("half_day") or HalfDayOption.NONE)

        # Check date overlap
        has_overlap = (new_start <= ex_end) and (new_end >= ex_start)
        if not has_overlap:
            continue

        # Half-day CL exception on the exact same date
        if (
            new_start == new_end == ex_start == ex_end
            and new_cat == LeaveCategory.CL
            and ex_cat == LeaveCategory.CL
            and new_half in (HalfDayOption.FIRST_HALF, HalfDayOption.SECOND_HALF)
            and ex_half in (HalfDayOption.FIRST_HALF, HalfDayOption.SECOND_HALF)
            and new_half != ex_half
        ):
            # Complementary halves on the same single date are permitted
            continue

        raise ValueError(
            f"Requested leave period ({new_start} to {new_end}) impermissibly overlaps with existing "
            f"{ex_cat.value} leave ({ex_start} to {ex_end}, status: {status})."
        )


def validate_substitute(
    applicant_user_id: int,
    substitute_user_id: int,
    substitute_leaves: List[Dict[str, Any]],
    resp_start: date,
    resp_end: date,
) -> None:
    """Validate substitute eligibility per BR-EL-014.

    - Substitute must be another employee (not applicant).
    - Substitute must have no overlapping pending or approved leave during responsibility period.
    """
    if applicant_user_id == substitute_user_id:
        raise ValueError("An employee cannot nominate themselves as a substitute.")

    for leave in substitute_leaves:
        status = leave.get("status")
        if status in ("REJECTED", "WITHDRAWN", "CANCELLED"):
            continue
        ex_start = leave["start_date"]
        ex_end = leave["end_date"]
        if (resp_start <= ex_end) and (resp_end >= ex_start):
            raise ValueError(
                f"Nominated substitute has conflicting leave ({ex_start} to {ex_end}, status: {status}) "
                "during the responsibility period."
            )


def calculate_year_end_transition(
    category: str | LeaveCategory,
    current_balance: Decimal,
) -> Tuple[Decimal, Decimal, Decimal]:
    """Calculate year-end balance transitions per BR-EL-002..008.

    Returns: (lapsed_days, carried_forward_days, converted_el_days)
    """
    cat = LeaveCategory(category)
    if cat in (LeaveCategory.CL, LeaveCategory.RH, LeaveCategory.SCL):
        # Lapse completely
        return (current_balance, Decimal("0.0"), Decimal("0.0"))

    if cat == LeaveCategory.VL:
        # Convert 2 VL : 1 EL including fractional conversion (BR-EL-007)
        converted_el = current_balance * Decimal("0.5")
        return (current_balance, Decimal("0.0"), converted_el)

    if cat in (LeaveCategory.EL, LeaveCategory.COL):
        # Carries forward
        return (Decimal("0.0"), current_balance, Decimal("0.0"))

    return (Decimal("0.0"), current_balance, Decimal("0.0"))


def calculate_resumption_adjustment(
    approved_days: Decimal,
    approved_start: date,
    approved_end: date,
    actual_resumption_date: date,
    category: str | LeaveCategory,
    half_day: Optional[str | HalfDayOption] = None,
    closed_dates: Optional[Set[date]] = None,
) -> Tuple[ResumptionOutcome, Decimal, Decimal]:
    """Calculate normal, early, or late resumption outcome per BR-EL-028.

    Returns: (ResumptionOutcome, actual_days, adjustment_days)
    - If actual_resumption_date == approved_end: NORMAL, no adjustment.
    - If actual_resumption_date < approved_end: EARLY, adjustment_days < 0 (credit/refund back to balance).
    - If actual_resumption_date > approved_end: LATE, adjustment_days > 0 (additional debit from balance).
    """
    if actual_resumption_date == approved_end:
        return (ResumptionOutcome.NORMAL, approved_days, Decimal("0.0"))

    actual_days = calculate_leave_days(
        category=category,
        start_date=approved_start,
        end_date=actual_resumption_date,
        half_day=half_day,
        closed_dates=closed_dates,
    )
    # adjustment_days = actual_days - approved_days
    # If early: actual_days < approved_days => adjustment < 0 (refund)
    # If late: actual_days > approved_days => adjustment > 0 (extra deduction)
    adjustment = actual_days - approved_days
    outcome = ResumptionOutcome.EARLY if actual_resumption_date < approved_end else ResumptionOutcome.LATE
    return (outcome, actual_days, adjustment)
