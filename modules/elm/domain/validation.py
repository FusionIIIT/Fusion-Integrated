"""Domain validation rules for Employee Leave Management."""

from __future__ import annotations

import datetime
from collections.abc import Container, Sequence
from decimal import Decimal

from .errors import (
    InsufficientBalanceError,
    InvalidDateRangeError,
    InvalidLeaveCategoryError,
    InvalidSubstituteError,
    OverlappingLeaveError,
    RestrictedHolidayMismatchError,
    VacationPeriodMismatchError,
)

VALID_CATEGORIES = frozenset({"CL", "RH", "SCL", "EL", "COL", "VL"})


def validate_category_and_dates(
    category: str,
    start_date: datetime.date,
    end_date: datetime.date,
    half_day: bool = False,
    half_day_type: str = "",
) -> None:
    """Validate leave category and basic date ordering."""
    if category not in VALID_CATEGORIES:
        raise InvalidLeaveCategoryError(f"Unsupported leave category '{category}'.")

    if start_date > end_date:
        raise InvalidDateRangeError("Start date cannot be after end date.")

    if half_day:
        if category != "CL":
            raise InvalidDateRangeError("Half day option is only allowed for Casual Leave (CL).")
        if start_date != end_date:
            raise InvalidDateRangeError(
                "Half day Casual Leave must start and end on the same date."
            )
        if half_day_type not in ("first_half", "second_half"):
            raise InvalidDateRangeError(
                "Half day Casual Leave must specify 'first_half' or 'second_half'."
            )


def is_overlapping_interval(
    start1: datetime.date,
    end1: datetime.date,
    start2: datetime.date,
    end2: datetime.date,
) -> bool:
    """Check if two date ranges overlap inclusive of boundaries."""
    return start1 <= end2 and end1 >= start2


def validate_non_overlapping(
    new_start: datetime.date,
    new_end: datetime.date,
    new_category: str,
    new_half_day: bool,
    new_half_day_type: str,
    existing_leaves: Sequence[dict],
) -> None:
    """Validate that new leave does not impermissibly overlap existing leaves (BR-EL-012).

    First-half and second-half CL on the same date are allowed.
    """
    for leave in existing_leaves:
        ex_start = leave["start_date"]
        ex_end = leave["end_date"]
        ex_cat = leave["leave_category"]
        ex_half = leave.get("half_day", False)
        ex_half_type = leave.get("half_day_type", "")

        if not is_overlapping_interval(new_start, new_end, ex_start, ex_end):
            continue

        # Special half-day CL non-overlap exception (BR-EL-012)
        if (
            new_category == "CL"
            and ex_cat == "CL"
            and new_half_day
            and ex_half
            and new_start == ex_start
            and new_start == new_end
            and ex_start == ex_end
            and new_half_day_type != ex_half_type
            and new_half_day_type in ("first_half", "second_half")
            and ex_half_type in ("first_half", "second_half")
        ):
            # Allowed non-overlapping halves of the same date
            continue

        raise OverlappingLeaveError(
            f"Requested leave period {new_start} to {new_end} impermissibly overlaps with "
            f"existing leave {ex_cat} from {ex_start} to {ex_end}."
        )


def validate_substitute(
    applicant_id: int,
    substitute_id: int | None,
    start_date: datetime.date,
    end_date: datetime.date,
    substitute_leaves: Sequence[dict],
) -> None:
    """Validate substitute eligibility (BR-EL-014).

    Substitute must not be applicant, and must not have active leave during the period.
    """
    if substitute_id is None:
        return

    if substitute_id == applicant_id:
        raise InvalidSubstituteError("Applicant cannot nominate themselves as substitute.")

    for leave in substitute_leaves:
        if is_overlapping_interval(start_date, end_date, leave["start_date"], leave["end_date"]):
            raise InvalidSubstituteError(
                f"Nominated substitute (ID {substitute_id}) has overlapping active leave "
                f"from {leave['start_date']} to {leave['end_date']}."
            )


def validate_available_balance(
    category: str,
    chargeable_days: Decimal,
    available_balance: Decimal,
) -> None:
    """Validate available balance (BR-EL-002..009)."""
    if available_balance < chargeable_days:
        raise InsufficientBalanceError(
            f"Insufficient {category} balance: required {chargeable_days} days, "
            f"available {available_balance} days."
        )


def validate_restricted_holiday(
    category: str,
    start_date: datetime.date,
    published_rh_dates: Container[datetime.date],
) -> None:
    """Validate RH against published RH calendar (BR-EL-003, BR-EL-031)."""
    if category != "RH":
        return
    if start_date not in published_rh_dates:
        raise RestrictedHolidayMismatchError(
            f"Date {start_date} is not an applicable Restricted Holiday in the published calendar."
        )


def validate_vacation_period(
    category: str,
    start_date: datetime.date,
    end_date: datetime.date,
    vacation_periods: Sequence[tuple[datetime.date, datetime.date]],
) -> None:
    """Validate VL falls completely within a published vacation period (BR-EL-006)."""
    if category != "VL":
        return

    for v_start, v_end in vacation_periods:
        if v_start <= start_date and end_date <= v_end:
            return

    raise VacationPeriodMismatchError(
        f"Vacation Leave ({start_date} to {end_date}) must fall within a "
        "published academic vacation period."
    )
