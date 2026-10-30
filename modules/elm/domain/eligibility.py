"""Validation and eligibility domain rules (Section 3, 5, 6)."""
from datetime import date
from decimal import Decimal

from modules.elm.domain.constants import (
    CL,
    EL,
    HALF_DAY_FIRST,
    HALF_DAY_SECOND,
    RH,
    VL,
)


class ValidationError(Exception):
    pass


def validate_eligibility_and_balance(
    category: str,
    employee_kind: str,
    requested_days: Decimal,
    available_balance: Decimal,
    start_date: date,
    is_vacation_period: bool = False,
    is_rh_calendar_day: bool = False,
) -> None:
    """Validate category eligibility and balance constraints."""
    if requested_days <= Decimal("0"):
        raise ValidationError("Requested leave days must be greater than zero.")

    if category == VL:
        if employee_kind != "faculty":
            raise ValidationError("Vacation Leave (VL) is applicable to faculty members only.")
        if not is_vacation_period:
            raise ValidationError("VL may be availed only during an applicable academic vacation period.")

    if category == RH and not is_rh_calendar_day:
        raise ValidationError("An RH request must correspond to an applicable Restricted Holiday in the calendar.")

    if requested_days > available_balance:
        raise ValidationError(
            f"Insufficient leave balance. Requested: {requested_days}, Available: {available_balance}."
        )


def check_overlap(
    new_start: date,
    new_end: date,
    new_category: str,
    new_half_day: str,
    existing_leaves: list[dict],
) -> bool:
    """Validate that the leave request does not impermissibly overlap (Section 5).

    First-half and second-half CL on the same date are not treated as overlapping
    when they occupy different halves.
    """
    for item in existing_leaves:
        e_start: date = item["start_date"]
        e_end: date = item["end_date"]
        e_cat: str = item.get("leave_category", "")
        e_half: str = item.get("half_day_type", "")

        # Check date range intersection
        if not (new_end < e_start or new_start > e_end):
            # Potential overlap
            if (
                new_start == new_end == e_start == e_end
                and new_category == CL
                and e_cat == CL
                and new_half_day in (HALF_DAY_FIRST, HALF_DAY_SECOND)
                and e_half in (HALF_DAY_FIRST, HALF_DAY_SECOND)
                and new_half_day != e_half
            ):
                # Allowed: different halves of the same date
                continue
            return True
    return False


def validate_substitute(
    applicant_id: int,
    substitute_id: int,
    start_date: date,
    end_date: date,
    substitute_leaves: list[dict],
) -> None:
    """Validate substitute eligibility (Section 6)."""
    if applicant_id == substitute_id:
        raise ValidationError("Applicant cannot be nominated as their own substitute.")

    for item in substitute_leaves:
        e_start: date = item["start_date"]
        e_end: date = item["end_date"]
        if not (end_date < e_start or start_date > e_end):
            raise ValidationError("Nominated substitute has active leave during the requested period.")
