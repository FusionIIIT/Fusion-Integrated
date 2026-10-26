"""Domain policy unit tests for Employee Leave Management.

Verifies pure domain logic: fractional Decimal calculations, substitute eligibility,
duty resumption adjustments, extension date boundaries, and year-end rollover math.
"""
from datetime import date
from decimal import Decimal

import pytest

from modules.elm.domain.policy import (
    MAX_EL_CARRY_FORWARD_CAP,
    ResumptionOutcome,
    calculate_leave_days,
    calculate_resumption_adjustment,
    compute_year_end_rollover,
    convert_vl_to_el,
    validate_leave_extension_dates,
    validate_substitute_nomination,
)


def test_calculate_leave_days():
    """Verify single-day, half-day, and multi-day duration calculations."""
    d1 = date(2026, 3, 2)
    d2 = date(2026, 3, 5)

    # Multi-day
    assert calculate_leave_days(d1, d2, half_day=False) == Decimal("4.0")

    # Single-day full
    assert calculate_leave_days(d1, d1, half_day=False) == Decimal("1.0")

    # Single-day half-day
    assert calculate_leave_days(d1, d1, half_day=True) == Decimal("0.5")

    # Inverted date validation
    with pytest.raises(ValueError, match="End date cannot be earlier than start date"):
        calculate_leave_days(d2, d1, half_day=False)

    # Half day multi-day validation
    with pytest.raises(ValueError, match="Half-day leave is permissible only for a single-day"):
        calculate_leave_days(d1, d2, half_day=True)


def test_convert_vl_to_el_fractional_precision():
    """Verify fractional Decimal-based 2:1 VL-to-EL conversion avoiding integer truncation."""
    # 15 VL converts to exactly 7.5 EL
    assert convert_vl_to_el(Decimal("15")) == Decimal("7.5")

    # 1 VL converts to 0.5 EL (integer truncation would produce 0)
    assert convert_vl_to_el(Decimal("1")) == Decimal("0.5")

    # 7 VL converts to 3.5 EL (integer truncation would produce 3)
    assert convert_vl_to_el(Decimal("7")) == Decimal("3.5")

    # 0 VL converts to 0.0 EL
    assert convert_vl_to_el(Decimal("0")) == Decimal("0.0")

    # Negative VL raises ValueError
    with pytest.raises(ValueError, match="cannot be negative"):
        convert_vl_to_el(Decimal("-1"))


def test_calculate_resumption_adjustment():
    """Verify duty resumption adjustment under normal, early, and late conditions."""
    scheduled_start = date(2026, 4, 1)
    scheduled_end = date(2026, 4, 10)  # 10 days leave

    # Normal resumption: resumed on scheduled end date (April 10)
    outcome_normal, adj_normal = calculate_resumption_adjustment(
        approved_start=scheduled_start,
        approved_end=scheduled_end,
        actual_resumption_date=scheduled_end,
    )
    assert outcome_normal == ResumptionOutcome.NORMAL
    assert adj_normal == Decimal("0.0")

    # Early resumption: resumed on April 6 (worked starting April 6)
    # Unused leave to refund: 10 - 6 = 4 days.
    outcome_early, adj_early = calculate_resumption_adjustment(
        approved_start=scheduled_start,
        approved_end=scheduled_end,
        actual_resumption_date=date(2026, 4, 6),
    )
    assert outcome_early == ResumptionOutcome.EARLY
    assert adj_early == Decimal("4.0")

    # Late resumption: resumed on April 15
    # Extra leave to deduct: 15 - 10 = 5 days.
    outcome_late, adj_late = calculate_resumption_adjustment(
        approved_start=scheduled_start,
        approved_end=scheduled_end,
        actual_resumption_date=date(2026, 4, 15),
    )
    assert outcome_late == ResumptionOutcome.LATE
    assert adj_late == Decimal("5.0")

    # Invalid resumption before scheduled start date
    with pytest.raises(ValueError, match="cannot be earlier than the approved leave start date"):
        calculate_resumption_adjustment(
            approved_start=scheduled_start,
            approved_end=scheduled_end,
            actual_resumption_date=date(2026, 3, 31),
        )


def test_validate_substitute_nomination():
    """Verify substitute eligibility rules (BR-EL-014)."""
    # Self-substitution rejection
    with pytest.raises(
        ValueError, match="Applicant cannot nominate themselves as their own substitute"
    ):
        validate_substitute_nomination(
            applicant_id=10,
            substitute_id=10,
            requires_substitute=True,
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 5),
            substitute_active_leaves=[],
        )

    # Overlapping active leave rejection
    existing_leaves = [(date(2026, 5, 3), date(2026, 5, 7))]
    with pytest.raises(ValueError, match="Nominated substitute has overlapping leave"):
        validate_substitute_nomination(
            applicant_id=10,
            substitute_id=20,
            requires_substitute=True,
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 5),
            substitute_active_leaves=existing_leaves,
        )

    # Valid non-overlapping nomination
    validate_substitute_nomination(
        applicant_id=10,
        substitute_id=20,
        requires_substitute=True,
        start_date=date(2026, 5, 8),
        end_date=date(2026, 5, 10),
        substitute_active_leaves=existing_leaves,
    )


def test_validate_leave_extension_dates():
    """Verify contiguous start date requirement for extensions (BR-EL-025)."""
    orig_end = date(2026, 6, 10)

    # Valid contiguous extension (starts on 2026-06-11)
    validate_leave_extension_dates(
        original_end_date=orig_end,
        extension_start_date=date(2026, 6, 11),
        extension_end_date=date(2026, 6, 15),
    )

    # Non-contiguous gap rejection (starts on 2026-06-12)
    with pytest.raises(ValueError, match="Extension start date must be"):
        validate_leave_extension_dates(
            original_end_date=orig_end,
            extension_start_date=date(2026, 6, 12),
            extension_end_date=date(2026, 6, 15),
        )


def test_compute_year_end_rollover():
    """Verify year-end rollover balance calculations (EL-UC-020 / BR-EL-002 to 009)."""
    current_balances = {
        "CL": (Decimal("8.0"), Decimal("4.0")),     # 4 unused -> lapses
        "RH": (Decimal("2.0"), Decimal("1.0")),     # 1 unused -> lapses
        "SCL": (Decimal("15.0"), Decimal("7.0")),   # 8 unused -> lapses
        "VL": (Decimal("60.0"), Decimal("45.0")),   # 15 unused -> converts to 7.5 EL
        "EL": (Decimal("300.0"), Decimal("5.0")),   # 295 unused + 7.5 = 302.5 -> capped at 300
        "COL": (Decimal("20.0"), Decimal("10.0")),  # 10 unused + 20 fresh = 30 carried forward
    }

    result = compute_year_end_rollover(
        user_id=1001,
        year=2026,
        current_balances=current_balances,
        is_faculty=True,
        max_el_cap=MAX_EL_CARRY_FORWARD_CAP,
    )

    # CL, RH, and SCL lapse completely
    assert result.cl_lapsed == Decimal("4.0")
    assert result.rh_lapsed == Decimal("1.0")
    assert result.scl_lapsed == Decimal("8.0")
    # Fresh quotas for next year
    assert result.next_year_balances["CL"] == Decimal("8.0")
    assert result.next_year_balances["RH"] == Decimal("2.0")
    assert result.next_year_balances["SCL"] == Decimal("15.0")

    # VL converts 2:1 to EL (15 VL -> 7.5 EL)
    assert result.vl_converted == Decimal("15.0")
    assert result.el_credited_from_vl == Decimal("7.5")
    assert result.next_year_balances["VL"] == Decimal("60.0")

    # EL cap is 300 days: 295 + 7.5 = 302.5 -> capped at 300.0
    assert result.el_carried_forward == Decimal("300.0")
    assert result.next_year_balances["EL"] == Decimal("300.0")
    assert result.next_year_balances["EL"] <= MAX_EL_CARRY_FORWARD_CAP

    # COL carry-forward adds 20 days: 10 unused + 20 fresh = 30 days
    assert result.col_carried_forward == Decimal("30.0")
    assert result.next_year_balances["COL"] == Decimal("30.0")
