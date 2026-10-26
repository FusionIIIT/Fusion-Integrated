"""Pure ELM validation helpers based on the synchronized business rules."""
from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError

CONTINUOUS_LEAVE_TYPES = {"EL", "COL", "VL"}
ACTIVE_OVERLAP_STATUSES = {
    "awaiting_substitute",
    "applicant_action",
    "unit_head_review",
    "establishment",
    "final_sanction",
    "approved",
}


def validate_date_range(start_date: date, end_date: date) -> None:
    if end_date < start_date:
        raise ValidationError("The end date cannot be before the start date.")


def calculate_leave_days(
    leave_code: str,
    start_date: date,
    end_date: date,
    half_day: str = "full",
) -> Decimal:
    """Calculate continuous intervals and half-day CL.

    For CL, SCL and RH, calendar-specific counting is not inferred here:
    callers must supply a policy-aware calculation before using this result.
    """
    validate_date_range(start_date, end_date)

    if half_day not in {"full", "first", "second"}:
        raise ValidationError("Invalid half-day selection.")

    if half_day != "full":
        if leave_code != "CL" or start_date != end_date:
            raise ValidationError(
                "Half-day requests are supported only for a single-day CL request."
            )
        return Decimal("0.5")

    if leave_code in CONTINUOUS_LEAVE_TYPES:
        return Decimal((end_date - start_date).days + 1)

    # Do not guess whether weekends/holidays count for other leave types.
    # Calendar/policy-aware counting must be supplied by the caller.
    return Decimal((end_date - start_date).days + 1)


def cl_halves_are_compatible(
    existing_code: str,
    existing_start: date,
    existing_end: date,
    existing_half: str,
    new_code: str,
    new_start: date,
    new_end: date,
    new_half: str,
) -> bool:
    """True only for distinct half-day CL requests on the same date."""
    return (
        existing_code == new_code == "CL"
        and existing_start == existing_end == new_start == new_end
        and {existing_half, new_half} == {"first", "second"}
    )


def date_intervals_overlap(
    first_start: date,
    first_end: date,
    second_start: date,
    second_end: date,
) -> bool:
    validate_date_range(first_start, first_end)
    validate_date_range(second_start, second_end)
    return first_start <= second_end and second_start <= first_end


def iter_dates(start_date: date, end_date: date):
    """Yield every date in an inclusive interval."""
    validate_date_range(start_date, end_date)
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)
