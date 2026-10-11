"""Pure Python domain tests for validation rules."""
from datetime import date
from decimal import Decimal

import pytest

from modules.elm.domain.constants import HalfDaySession, LeaveCategory
from modules.elm.domain.validation import (
    ExistingLeaveInterval,
    validate_balance_sufficient,
    validate_category_eligibility,
    validate_overlap,
    validate_rh_date,
    validate_substitute_eligibility,
    validate_vacation_period,
)


def test_category_eligibility():
    """BR-EL-001, BR-EL-006: VL is faculty only."""
    # Faculty can take VL and CL
    validate_category_eligibility(LeaveCategory.VL, user_kind="faculty")
    validate_category_eligibility(LeaveCategory.CL, user_kind="faculty")

    # Staff cannot take VL
    with pytest.raises(ValueError, match="only available for faculty"):
        validate_category_eligibility(LeaveCategory.VL, user_kind="staff")

    # Invalid category
    with pytest.raises(ValueError, match="Invalid leave category"):
        validate_category_eligibility("INVALID", user_kind="faculty")


def test_balance_sufficient():
    # Sufficient
    validate_balance_sufficient(Decimal("8.00"), Decimal("2.00"), LeaveCategory.CL)
    validate_balance_sufficient(Decimal("2.00"), Decimal("2.00"), LeaveCategory.CL)

    # Insufficient
    with pytest.raises(ValueError, match="Insufficient leave balance"):
        validate_balance_sufficient(Decimal("1.50"), Decimal("2.00"), LeaveCategory.CL)


def test_overlap_detection():
    """BR-EL-012: Overlap check including half-day exception."""
    existing = [
        ExistingLeaveInterval(
            start_date=date(2026, 10, 12),
            end_date=date(2026, 10, 14),
            is_half_day=False,
            half_day_session=None,
            status="approved",
            category="CL",
        )
    ]

    # Overlapping interval raises
    with pytest.raises(ValueError, match="overlaps with an existing"):
        validate_overlap(existing, date(2026, 10, 13), date(2026, 10, 16))

    # Non-overlapping passes
    validate_overlap(existing, date(2026, 10, 15), date(2026, 10, 18))


def test_half_day_non_overlap_exception():
    """BR-EL-012: Same date first_half and second_half do not conflict."""
    existing_first_half = [
        ExistingLeaveInterval(
            start_date=date(2026, 10, 14),
            end_date=date(2026, 10, 14),
            is_half_day=True,
            half_day_session=HalfDaySession.FIRST_HALF.value,
            status="approved",
            category="CL",
        )
    ]

    # Same day, second_half: ALLOWED
    validate_overlap(
        existing_first_half,
        date(2026, 10, 14),
        date(2026, 10, 14),
        is_half_day=True,
        half_day_session=HalfDaySession.SECOND_HALF.value,
    )

    # Same day, same session (first_half): CONFLICT
    with pytest.raises(ValueError, match="overlaps"):
        validate_overlap(
            existing_first_half,
            date(2026, 10, 14),
            date(2026, 10, 14),
            is_half_day=True,
            half_day_session=HalfDaySession.FIRST_HALF.value,
        )

    # Same day, full day request against half-day existing: CONFLICT
    with pytest.raises(ValueError, match="overlaps"):
        validate_overlap(
            existing_first_half,
            date(2026, 10, 14),
            date(2026, 10, 14),
            is_half_day=False,
        )


def test_substitute_eligibility():
    """BR-EL-014: Cannot substitute self; substitute must not have active overlapping leave."""
    applicant_id = 100
    sub_id = 200

    # Self-substitution fails
    with pytest.raises(ValueError, match="cannot nominate themselves as a substitute"):
        validate_substitute_eligibility(
            applicant_id,
            applicant_id,
            "faculty",
            [],
            date(2026, 10, 12),
            date(2026, 10, 14),
        )

    # Substitute has overlapping leave
    sub_existing = [
        ExistingLeaveInterval(
            start_date=date(2026, 10, 10),
            end_date=date(2026, 10, 15),
            is_half_day=False,
            half_day_session=None,
            status="approved",
            category="CL",
        )
    ]
    with pytest.raises(ValueError, match="has an overlapping"):
        validate_substitute_eligibility(
            applicant_id,
            sub_id,
            "faculty",
            sub_existing,
            date(2026, 10, 12),
            date(2026, 10, 14),
        )


def test_rh_date_validation():
    """BR-EL-003, BR-EL-031: RH must match published restricted holiday."""
    published = {date(2026, 3, 25), date(2026, 11, 4)}

    # Valid
    validate_rh_date(date(2026, 3, 25), published)

    # Not in published calendar
    with pytest.raises(ValueError, match="not listed as an applicable Restricted Holiday"):
        validate_rh_date(date(2026, 3, 26), published)


def test_vacation_period_validation():
    """BR-EL-006: VL must fall within vacation intervals."""
    vac_intervals = [
        (date(2026, 5, 1), date(2026, 6, 30)),
        (date(2026, 12, 1), date(2026, 12, 31)),
    ]

    # Within summer vacation
    validate_vacation_period(date(2026, 5, 10), date(2026, 5, 20), vac_intervals)

    # Outside vacation periods
    with pytest.raises(ValueError, match="must fall entirely within an applicable"):
        validate_vacation_period(date(2026, 7, 1), date(2026, 7, 10), vac_intervals)
