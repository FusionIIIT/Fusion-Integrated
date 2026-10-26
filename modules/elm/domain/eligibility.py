"""Eligibility and validation rules for ELM.

Pure Python: no Django dependencies.
Enforces:
- BR-EL-001: Supported leave-category eligibility
- BR-EL-003: RH calendar validation
- BR-EL-006: Faculty VL vacation period applicability
- BR-EL-012: Applicant non-overlap with half-day CL exception
- BR-EL-013: Station Leave coupling
- BR-EL-014: Substitute eligibility (not applicant, no overlapping leave)
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Container, Sequence

from modules.elm.domain.constants import (
    HalfDayPeriod,
    LeaveCategory,
)


@dataclass(frozen=True)
class ExistingLeaveSpan:
    """Represents an active pending or approved leave for overlap checks."""
    leave_id: int
    category: str | LeaveCategory
    start_date: datetime.date
    end_date: datetime.date
    is_half_day: bool = False
    half_day_period: str | HalfDayPeriod = HalfDayPeriod.NONE


@dataclass(frozen=True)
class VacationPeriod:
    """Vacation interval from Academic Calendar (EXT-01)."""
    name: str
    start_date: datetime.date
    end_date: datetime.date


@dataclass(frozen=True)
class ValidationResult:
    is_valid: bool
    error_code: str = ""
    error_message: str = ""


def check_category_eligibility(
    category: str | LeaveCategory,
    is_faculty: bool,
) -> ValidationResult:
    """Validate category eligibility by employee kind (Faculty vs Staff).

    - VL is exclusive to Faculty (BR-EL-006).
    - Other categories (CL, RH, SCL, COL, EL) are open to employees.
    """
    try:
        cat = LeaveCategory(category)
    except ValueError:
        return ValidationResult(
            is_valid=False,
            error_code="invalid_category",
            error_message=f"Category '{category}' is not a supported baseline leave category.",
        )

    if cat == LeaveCategory.VL and not is_faculty:
        return ValidationResult(
            is_valid=False,
            error_code="vl_faculty_only",
            error_message="Vacation Leave (VL) is only available to faculty employees.",
        )

    return ValidationResult(is_valid=True)


def check_rh_calendar_applicability(
    requested_date: datetime.date,
    published_rh_dates: Container[datetime.date],
) -> ValidationResult:
    """BR-EL-003 / BR-EL-031: RH request must match an applicable Restricted Holiday."""
    if requested_date not in published_rh_dates:
        return ValidationResult(
            is_valid=False,
            error_code="rh_not_on_calendar",
            error_message=f"Date {requested_date} is not listed in the published Restricted Holiday (RH) calendar.",
        )
    return ValidationResult(is_valid=True)


def check_vl_vacation_applicability(
    start_date: datetime.date,
    end_date: datetime.date,
    vacation_periods: Sequence[VacationPeriod],
) -> ValidationResult:
    """BR-EL-006: VL may be availed ONLY during an applicable Academic Calendar vacation period."""
    # The entire leave span [start_date, end_date] must fall within at least one vacation period
    for vp in vacation_periods:
        if vp.start_date <= start_date and end_date <= vp.end_date:
            return ValidationResult(is_valid=True)

    return ValidationResult(
        is_valid=False,
        error_code="vl_outside_vacation_period",
        error_message=(
            f"The requested interval {start_date} to {end_date} falls outside "
            "published Academic Calendar vacation periods."
        ),
    )


def check_applicant_overlap(
    category: str | LeaveCategory,
    start_date: datetime.date,
    end_date: datetime.date,
    is_half_day: bool,
    half_day_period: str | HalfDayPeriod,
    existing_leaves: Sequence[ExistingLeaveSpan],
) -> ValidationResult:
    """BR-EL-012: Prevent impermissible overlap with active pending or approved leave.

    Special exception: First-half and second-half CL on the same date are
    non-overlapping when they occupy different halves.
    """
    cat = LeaveCategory(category)
    period = HalfDayPeriod(half_day_period) if is_half_day else HalfDayPeriod.NONE

    for ex in existing_leaves:
        # Standard date overlap: (start_date <= ex.end_date) and (end_date >= ex.start_date)
        if start_date <= ex.end_date and end_date >= ex.start_date:
            # Check half-day CL non-overlap exception (BR-EL-012)
            if (
                cat == LeaveCategory.CL
                and ex.category == LeaveCategory.CL
                and is_half_day
                and ex.is_half_day
                and start_date == ex.start_date
                and end_date == ex.end_date
            ):
                ex_period = HalfDayPeriod(ex.half_day_period)
                if period != ex_period and period != HalfDayPeriod.NONE and ex_period != HalfDayPeriod.NONE:
                    # Non-overlapping halves on the exact same date!
                    continue

            return ValidationResult(
                is_valid=False,
                error_code="overlapping_leave",
                error_message=(
                    f"Requested leave interval {start_date} to {end_date} impermissibly "
                    f"overlaps active leave #{ex.leave_id} ({ex.start_date} to {ex.end_date})."
                ),
            )

    return ValidationResult(is_valid=True)


def check_substitute_eligibility(
    applicant_id: int,
    substitute_id: int,
    start_date: datetime.date,
    end_date: datetime.date,
    substitute_active_leaves: Sequence[ExistingLeaveSpan],
    is_employee: bool = True,
) -> ValidationResult:
    """BR-EL-014: Substitute must be another employee, not the applicant,

    and have NO overlapping pending or approved leave during the responsibility period.
    """
    if not is_employee:
        return ValidationResult(
            is_valid=False,
            error_code="substitute_not_employee",
            error_message="The nominated substitute must be a recognized employee.",
        )

    if applicant_id == substitute_id:
        return ValidationResult(
            is_valid=False,
            error_code="substitute_self_nomination",
            error_message="An employee cannot nominate themselves as their own substitute.",
        )

    for ex in substitute_active_leaves:
        if start_date <= ex.end_date and end_date >= ex.start_date:
            return ValidationResult(
                is_valid=False,
                error_code="substitute_has_overlapping_leave",
                error_message=(
                    f"The nominated substitute has conflicting active leave #{ex.leave_id} "
                    f"({ex.start_date} to {ex.end_date}) during the responsibility period."
                ),
            )

    return ValidationResult(is_valid=True)


def check_station_leave_coupling(
    is_station_leave: bool,
    leave_start: datetime.date,
    leave_end: datetime.date,
    station_start: datetime.date | None,
    station_end: datetime.date | None,
    station_destination: str = "",
) -> ValidationResult:
    """BR-EL-013: Station Leave is coupled into the same application."""
    if not is_station_leave:
        return ValidationResult(is_valid=True)

    if not station_destination.strip():
        return ValidationResult(
            is_valid=False,
            error_code="missing_station_destination",
            error_message="Station leave requires specifying the out-of-station destination.",
        )

    if station_start is None or station_end is None:
        return ValidationResult(
            is_valid=False,
            error_code="missing_station_dates",
            error_message="Station leave requires departure and return dates.",
        )

    if station_end < station_start:
        return ValidationResult(
            is_valid=False,
            error_code="invalid_station_dates",
            error_message="Station leave return date cannot be before departure date.",
        )

    return ValidationResult(is_valid=True)
