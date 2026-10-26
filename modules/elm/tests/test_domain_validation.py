import datetime
from decimal import Decimal

import pytest

from modules.elm.domain.errors import (
    InsufficientBalanceError,
    InvalidDateRangeError,
    InvalidSubstituteError,
    OverlappingLeaveError,
    RestrictedHolidayMismatchError,
    VacationPeriodMismatchError,
)
from modules.elm.domain.validation import (
    validate_available_balance,
    validate_category_and_dates,
    validate_non_overlapping,
    validate_restricted_holiday,
    validate_substitute,
    validate_vacation_period,
)


def test_validate_dates_and_half_day():
    d1 = datetime.date(2026, 11, 2)
    d2 = datetime.date(2026, 11, 1)
    with pytest.raises(InvalidDateRangeError, match="cannot be after"):
        validate_category_and_dates("CL", d1, d2)

    with pytest.raises(
        InvalidDateRangeError, match="Half day option is only allowed for Casual Leave"
    ):
        validate_category_and_dates("EL", d1, d1, half_day=True, half_day_type="first_half")

    with pytest.raises(InvalidDateRangeError, match="must specify 'first_half' or 'second_half'"):
        validate_category_and_dates("CL", d1, d1, half_day=True, half_day_type="")


def test_overlap_detection_normal_conflict():
    """BR-EL-012: Prevent impermissible overlap with active leave."""
    existing = [
        {
            "start_date": datetime.date(2026, 11, 10),
            "end_date": datetime.date(2026, 11, 15),
            "leave_category": "EL",
            "half_day": False,
        }
    ]

    with pytest.raises(OverlappingLeaveError, match="impermissibly overlaps"):
        validate_non_overlapping(
            new_start=datetime.date(2026, 11, 12),
            new_end=datetime.date(2026, 11, 18),
            new_category="CL",
            new_half_day=False,
            new_half_day_type="",
            existing_leaves=existing,
        )


def test_overlap_detection_half_day_cl_exception():
    """BR-EL-012: First-half and second-half CL on same date are non-overlapping."""
    date = datetime.date(2026, 11, 10)
    existing = [
        {
            "start_date": date,
            "end_date": date,
            "leave_category": "CL",
            "half_day": True,
            "half_day_type": "first_half",
        }
    ]

    # Different half on same date -> ALLOWED (no exception)
    validate_non_overlapping(
        new_start=date,
        new_end=date,
        new_category="CL",
        new_half_day=True,
        new_half_day_type="second_half",
        existing_leaves=existing,
    )

    # Same half on same date -> OVERLAP ERROR
    with pytest.raises(OverlappingLeaveError):
        validate_non_overlapping(
            new_start=date,
            new_end=date,
            new_category="CL",
            new_half_day=True,
            new_half_day_type="first_half",
            existing_leaves=existing,
        )


def test_substitute_validation():
    """BR-EL-014: Substitute must not be applicant, and must have no overlapping leave."""
    applicant_id = 101
    substitute_id = 202
    start = datetime.date(2026, 11, 2)
    end = datetime.date(2026, 11, 5)

    with pytest.raises(InvalidSubstituteError, match="Applicant cannot nominate themselves"):
        validate_substitute(applicant_id, applicant_id, start, end, [])

    sub_leaves = [
        {
            "start_date": datetime.date(2026, 11, 3),
            "end_date": datetime.date(2026, 11, 4),
        }
    ]
    with pytest.raises(InvalidSubstituteError, match="overlapping active leave"):
        validate_substitute(applicant_id, substitute_id, start, end, sub_leaves)


def test_available_balance_validation():
    """BR-EL-002..009: Insufficient balance blocks request."""
    with pytest.raises(InsufficientBalanceError, match="Insufficient CL balance"):
        validate_available_balance("CL", Decimal("5.0"), Decimal("4.5"))

    # Passes when sufficient
    validate_available_balance("CL", Decimal("4.0"), Decimal("4.5"))


def test_rh_calendar_validation():
    """BR-EL-003, BR-EL-031: RH request must match published calendar."""
    rh_date = datetime.date(2026, 10, 24)
    published_rhs = {rh_date}

    validate_restricted_holiday("RH", rh_date, published_rhs)

    invalid_date = datetime.date(2026, 10, 25)
    with pytest.raises(RestrictedHolidayMismatchError):
        validate_restricted_holiday("RH", invalid_date, published_rhs)


def test_vl_vacation_period_validation():
    """BR-EL-006: VL must fall within an academic vacation period."""
    vacations = [
        (datetime.date(2026, 12, 15), datetime.date(2026, 12, 31)),
    ]

    # Valid within vacation
    validate_vacation_period(
        "VL", datetime.date(2026, 12, 20), datetime.date(2026, 12, 25), vacations
    )

    # Outside vacation -> error
    with pytest.raises(VacationPeriodMismatchError):
        validate_vacation_period(
            "VL", datetime.date(2026, 12, 10), datetime.date(2026, 12, 20), vacations
        )
