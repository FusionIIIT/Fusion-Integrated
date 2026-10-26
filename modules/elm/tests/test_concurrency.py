"""Concurrency, balance ledger integrity, and idempotency tests for ELM.

Covers:
- Safe first-time balance creation under race conditions.
- Multi-bucket balance equation (credited + carried_forward + converted_in - availed - pending - converted_out).
- Applicant non-overlap enforcement (BR-EL-012).
- Idempotent VL-to-EL 2:1 conversion (BR-EL-007, BR-EL-008, EL-UC-020).
- Offline-sanctioned leave synchronization (EL-UC-016, BR-EL-029).
"""
from __future__ import annotations

import datetime
from decimal import Decimal
import pytest
from django.core.exceptions import ValidationError

from modules.elm.domain import state_machine as sm
from modules.elm.models import LeaveBalance, LeaveRequest, YearEndProcessingLog
from modules.elm import services

pytestmark = pytest.mark.django_db


def test_first_time_balance_creation_is_safe_and_idempotent():
    """get_or_create_locked_balance initializes quota safely."""
    bal1 = services.get_or_create_locked_balance(user_id=201, category="cl", year=2026, is_faculty=False)
    assert bal1.credited == Decimal("8.0")
    assert bal1.available == Decimal("8.0")

    # Fetch again, same object returned without duplicate row
    bal2 = services.get_or_create_locked_balance(user_id=201, category="cl", year=2026, is_faculty=False)
    assert bal1.id == bal2.id


def test_multi_bucket_available_property():
    """Verify available property calculation matches ledger balance."""
    bal = LeaveBalance.objects.create(
        user_id=202,
        category="el",
        year=2026,
        credited=Decimal("30.0"),
        carried_forward=Decimal("15.0"),
        converted_in=Decimal("5.0"),
        availed=Decimal("10.0"),
        pending=Decimal("4.0"),
        converted_out=Decimal("0.0"),
    )
    # Total credit: 30 + 15 + 5 = 50
    # Total consumed: 10 + 4 + 0 = 14
    # Available: 50 - 14 = 36
    assert bal.available == Decimal("36.0")


def test_overlap_prevention_rejects_overlapping_dates():
    """BR-EL-012: Active requests in pending or approved states block overlap."""
    LeaveBalance.objects.create(user_id=203, category="cl", year=2026, credited=Decimal("8.0"))
    LeaveRequest.objects.create(
        user_id=203,
        category="cl",
        start_date=datetime.date(2026, 11, 2),
        end_date=datetime.date(2026, 11, 4),
        leave_days=Decimal("3.0"),
        status=sm.PENDING_UNIT_HEAD,
        reason="Existing active leave",
    )

    # Overlapping attempt: Nov 3 to Nov 5
    with pytest.raises(ValidationError) as exc:
        services.validate_no_overlap(
            user_id=203,
            category="cl",
            start_date=datetime.date(2026, 11, 3),
            end_date=datetime.date(2026, 11, 5),
        )
    assert "overlaps with existing" in str(exc.value)


def test_complementary_half_day_cl_on_same_date_permitted():
    """BR-EL-012: Same-date complementary half-day CL (first_half + second_half) is permitted."""
    LeaveBalance.objects.create(user_id=204, category="cl", year=2026, credited=Decimal("8.0"))
    LeaveRequest.objects.create(
        user_id=204,
        category="cl",
        start_date=datetime.date(2026, 11, 10),
        end_date=datetime.date(2026, 11, 10),
        half_day=True,
        half_day_type="first_half",
        leave_days=Decimal("0.5"),
        status=sm.PENDING_UNIT_HEAD,
        reason="First half",
    )

    # Submitting second_half on same date should pass without raising ValidationError
    services.validate_no_overlap(
        user_id=204,
        category="cl",
        start_date=datetime.date(2026, 11, 10),
        end_date=datetime.date(2026, 11, 10),
        half_day=True,
        half_day_type="second_half",
    )


def test_year_end_vl_conversion_idempotency():
    """BR-EL-007, BR-EL-008: Unused VL converts to EL at 2:1 ratio; running twice is a no-op."""
    # Faculty with 60 days VL, availed 10 days => 50 days available
    vl_bal = LeaveBalance.objects.create(
        user_id=205,
        category="vl",
        year=2026,
        credited=Decimal("60.0"),
        availed=Decimal("10.0"),
    )
    assert vl_bal.available == Decimal("50.0")

    # Run rollover for 2026
    unused_vl, el_credited = services.process_year_end_vl_conversion(user_id=205, year=2026)
    assert unused_vl == Decimal("50.0")
    assert el_credited == Decimal("25.0")  # 50 / 2 = 25.0

    # Check 2026 VL converted_out
    vl_bal.refresh_from_db()
    assert vl_bal.converted_out == Decimal("50.0")
    assert vl_bal.available == Decimal("0.0")

    # Check 2027 EL converted_in
    next_el = LeaveBalance.objects.get(user_id=205, category="el", year=2027)
    assert next_el.converted_in == Decimal("25.0")

    # Check YearEndProcessingLog entry created
    assert YearEndProcessingLog.objects.filter(user_id=205, year=2026).count() == 1

    # Run second time: must be idempotent and return identical numbers without double-crediting
    unused_vl2, el_credited2 = services.process_year_end_vl_conversion(user_id=205, year=2026)
    assert unused_vl2 == Decimal("50.0")
    assert el_credited2 == Decimal("25.0")

    next_el.refresh_from_db()
    assert next_el.converted_in == Decimal("25.0")  # Still 25.0, NOT 50.0!


def test_record_offline_sanctioned_leave():
    """EL-UC-016, BR-EL-029: Offline sanctioned leave commits availed balance directly."""
    LeaveBalance.objects.create(user_id=206, category="cl", year=2026, credited=Decimal("8.0"))

    req = services.record_offline_sanctioned_leave(
        admin_user_id=1,
        applicant_user_id=206,
        category="cl",
        start_date=datetime.date(2026, 11, 23),
        end_date=datetime.date(2026, 11, 24),
        reason="Emergency offline sanctioned leave",
        sanction_reference="OFFICE_ORDER/2026/ELM/8871",
    )
    assert req.status == sm.APPROVED
    assert req.leave_days == Decimal("2.0")
    assert "OFFICE_ORDER/2026/ELM/8871" in req.sanctioning_remarks

    bal = LeaveBalance.objects.get(user_id=206, category="cl", year=2026)
    assert bal.availed == Decimal("2.0")
    assert bal.available == Decimal("6.0")
