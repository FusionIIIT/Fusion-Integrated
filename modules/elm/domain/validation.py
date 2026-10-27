"""Validation rules implementing BR-EL-001..015."""
from datetime import date
from typing import List, Tuple, Optional


class ValidationError(Exception):
    pass


def validate_category_eligibility(category: str, employee_kind: str) -> None:
    """Validate category eligibility based on employee kind (Faculty vs Staff).

    BR-EL-001, BR-EL-005, BR-EL-006.
    """
    valid_categories = {"CL", "RH", "SCL", "EL", "COL", "VL"}
    if category not in valid_categories:
        raise ValidationError(f"Invalid leave category: {category}")

    if category == "VL" and employee_kind != "faculty":
        raise ValidationError("Vacation Leave (VL) is admissible only for Faculty employees.")


def validate_restricted_holiday(
    category: str,
    start_date: date,
    end_date: date,
    published_rh_dates: set[date],
) -> None:
    """Validate that RH application matches a published Restricted Holiday (BR-EL-003)."""
    if category != "RH":
        return

    if start_date != end_date:
        raise ValidationError("Restricted Holiday (RH) must be requested for a single holiday date.")

    if start_date not in published_rh_dates:
        raise ValidationError(f"Date {start_date} is not listed in the currently effective Restricted Holiday calendar.")


def validate_vacation_period(
    category: str,
    start_date: date,
    end_date: date,
    vacation_intervals: List[Tuple[date, date]],
) -> None:
    """Validate that VL falls entirely within an active vacation period (BR-EL-006)."""
    if category != "VL":
        return

    falls_within = any(
        vac_start <= start_date and end_date <= vac_end
        for vac_start, vac_end in vacation_intervals
    )
    if not falls_within:
        raise ValidationError(
            "Vacation Leave (VL) may be availed only during an active vacation period in the Academic Calendar."
        )


def validate_no_overlap(
    new_start: date,
    new_end: date,
    new_half_day: str,
    existing_leaves: List[Tuple[date, date, str]],
) -> None:
    """Validate that leave does not impermissibly overlap existing leaves (BR-EL-012).

    First-half and second-half CL on the same date are allowed.
    """
    for ex_start, ex_end, ex_half in existing_leaves:
        # Check date overlap
        has_date_overlap = max(new_start, ex_start) <= min(new_end, ex_end)
        if not has_date_overlap:
            continue

        # If on the same single day, check if one is first-half and the other is second-half
        if new_start == new_end == ex_start == ex_end:
            if (new_half_day == "first_half" and ex_half == "second_half") or (
                new_half_day == "second_half" and ex_half == "first_half"
            ):
                continue  # Permissible half-day coexistence

        raise ValidationError(
            f"Requested leave period ({new_start} to {new_end}) overlaps with an existing leave ({ex_start} to {ex_end})."
        )


def validate_substitute(
    applicant_id: int,
    substitute_id: Optional[int],
    start_date: date,
    end_date: date,
    substitute_leaves: List[Tuple[date, date]],
) -> None:
    """Validate substitute eligibility (BR-EL-014).

    Substitute must be another employee, not the applicant, and cannot have
    overlapping leave during the responsibility period.
    """
    if not substitute_id:
        return

    if applicant_id == substitute_id:
        raise ValidationError("Applicant cannot nominate themselves as their own substitute.")

    for sub_start, sub_end in substitute_leaves:
        if max(start_date, sub_start) <= min(end_date, sub_end):
            raise ValidationError(
                f"Nominated substitute has approved or pending leave ({sub_start} to {sub_end}) during the requested period."
            )
