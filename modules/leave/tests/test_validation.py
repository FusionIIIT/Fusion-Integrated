# Tests for ELM application validation (BR-EL-012, BR-EL-013, BR-EL-036)
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from core.api.exceptions import BadRequestError, ConflictError, PermissionDeniedError
from modules.leave.domain.constants import (
    HALF_DAY_FIRST,
    HALF_DAY_NONE,
    HALF_DAY_SECOND,
    LEAVE_TYPE_CL,
    LEAVE_TYPE_EL,
    STATUS_APPROVED,
    STATUS_PENDING,
)
from modules.leave.domain.validation import (
    validate_approver_identity,
    validate_balance_sufficiency,
    validate_leave_overlap,
    validate_station_leave,
)


def test_station_leave_validation():
    """BR-EL-013: Station leave requires destination address."""
    with pytest.raises(BadRequestError, match="Station leave address is mandatory"):
        validate_station_leave(is_station_leave=True, station_leave_address="")

    with pytest.raises(BadRequestError, match="Station leave address is mandatory"):
        validate_station_leave(is_station_leave=True, station_leave_address="   ")

    # Valid address passes
    validate_station_leave(is_station_leave=True, station_leave_address="New Delhi, India")
    # Non-station leave passes with empty address
    validate_station_leave(is_station_leave=False, station_leave_address="")


def test_leave_overlap_conflict():
    """BR-EL-012: New application overlapping active leave raises ConflictError."""
    existing = [
        SimpleNamespace(
            id=10,
            leave_type=LEAVE_TYPE_EL,
            start_date=date(2026, 11, 10),
            end_date=date(2026, 11, 15),
            half_day=HALF_DAY_NONE,
            status=STATUS_APPROVED,
        )
    ]

    # Partial overlap
    with pytest.raises(ConflictError, match="overlaps with existing APPROVED"):
        validate_leave_overlap(
            date(2026, 11, 14),
            date(2026, 11, 18),
            LEAVE_TYPE_EL,
            HALF_DAY_NONE,
            existing,
        )

    # Identical dates
    with pytest.raises(ConflictError, match="overlaps with existing APPROVED"):
        validate_leave_overlap(
            date(2026, 11, 10),
            date(2026, 11, 15),
            LEAVE_TYPE_CL,
            HALF_DAY_NONE,
            existing,
        )

    # Non-overlapping passes
    validate_leave_overlap(
        date(2026, 11, 16),
        date(2026, 11, 20),
        LEAVE_TYPE_EL,
        HALF_DAY_NONE,
        existing,
    )


def test_half_day_cl_complementary_non_overlap():
    """BR-EL-012: First-half and second-half CL on the same date do NOT overlap."""
    single_date = date(2026, 11, 12)
    existing = [
        SimpleNamespace(
            id=22,
            leave_type=LEAVE_TYPE_CL,
            start_date=single_date,
            end_date=single_date,
            half_day=HALF_DAY_FIRST,
            status=STATUS_PENDING,
        )
    ]

    # Second half on same date is allowed
    validate_leave_overlap(
        single_date,
        single_date,
        LEAVE_TYPE_CL,
        HALF_DAY_SECOND,
        existing,
    )

    # Same half on same date must conflict
    with pytest.raises(ConflictError, match="overlaps with existing PENDING"):
        validate_leave_overlap(
            single_date,
            single_date,
            LEAVE_TYPE_CL,
            HALF_DAY_FIRST,
            existing,
        )


def test_balance_sufficiency():
    """Ensures requested days do not exceed available balance."""
    # Sufficient
    validate_balance_sufficiency(
        allocated=Decimal("8.00"),
        used=Decimal("2.00"),
        requested_days=Decimal("6.00"),
        leave_type=LEAVE_TYPE_CL,
    )

    # Insufficient
    with pytest.raises(BadRequestError, match="Insufficient balance for CL"):
        validate_balance_sufficiency(
            allocated=Decimal("8.00"),
            used=Decimal("5.00"),
            requested_days=Decimal("4.00"),
            leave_type=LEAVE_TYPE_CL,
        )


def test_self_approval_prevention():
    """BR-EL-036: Approvers cannot approve their own applications."""
    with pytest.raises(PermissionDeniedError, match="strictly prohibited"):
        validate_approver_identity(applicant_user_id=101, approver_user_id=101)

    # Different approver passes
    validate_approver_identity(applicant_user_id=101, approver_user_id=202)
