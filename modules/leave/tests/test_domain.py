import pytest
from datetime import date
from decimal import Decimal
from django.core.exceptions import ValidationError
from modules.leave.models import (
    LeaveApplication,
    LeaveCategory,
    HalfDaySlot,
    LeaveStatus,
    HolidayCalendar,
)
from modules.leave.domain.rules import (
    is_half_day_cl_valid,
    calculate_leave_days,
    validate_leave_application,
)


@pytest.mark.django_db
def test_half_day_cl_validation():
    # Half-day is valid strictly for CL on a single date
    assert is_half_day_cl_valid(LeaveCategory.CL, HalfDaySlot.FIRST_HALF, date(2026, 11, 2), date(2026, 11, 2))
    assert is_half_day_cl_valid(LeaveCategory.CL, HalfDaySlot.SECOND_HALF, date(2026, 11, 2), date(2026, 11, 2))
    assert is_half_day_cl_valid(LeaveCategory.CL, HalfDaySlot.NONE, date(2026, 11, 2), date(2026, 11, 5))

    # Invalid: Half-day on multi-day range
    assert not is_half_day_cl_valid(LeaveCategory.CL, HalfDaySlot.FIRST_HALF, date(2026, 11, 2), date(2026, 11, 3))

    # Invalid: Half-day for categories other than CL
    assert not is_half_day_cl_valid(LeaveCategory.EL, HalfDaySlot.FIRST_HALF, date(2026, 11, 2), date(2026, 11, 2))
    assert not is_half_day_cl_valid(LeaveCategory.RH, HalfDaySlot.FIRST_HALF, date(2026, 11, 2), date(2026, 11, 2))


@pytest.mark.django_db
def test_continuous_vs_working_day_counting():
    # 2026-11-06 (Friday) to 2026-11-09 (Monday): 4 calendar days (includes Sat Nov 7, Sun Nov 8)
    d_start = date(2026, 11, 6)
    d_end = date(2026, 11, 9)

    # EL: Continuous count includes weekend -> 4 days
    assert calculate_leave_days(LeaveCategory.EL, d_start, d_end, HalfDaySlot.NONE) == Decimal("4.0")
    # COL: Continuous count -> 4 days
    assert calculate_leave_days(LeaveCategory.COL, d_start, d_end, HalfDaySlot.NONE) == Decimal("4.0")

    # CL: Working days only -> Friday (1) + Monday (1) = 2 days
    assert calculate_leave_days(LeaveCategory.CL, d_start, d_end, HalfDaySlot.NONE) == Decimal("2")

    # Half-day count is 0.5
    assert calculate_leave_days(LeaveCategory.CL, d_start, d_start, HalfDaySlot.FIRST_HALF) == Decimal("0.5")


@pytest.mark.django_db
def test_overlap_validation_and_half_day_exception():
    # Base application: full day on 2026-11-10
    app1 = LeaveApplication.objects.create(
        user_id=101,
        category=LeaveCategory.CL,
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 10),
        status=LeaveStatus.APPROVED,
    )

    # Duplicate full-day application on same date -> Must fail
    app2 = LeaveApplication(
        user_id=101,
        category=LeaveCategory.CL,
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 10),
        status=LeaveStatus.SUBMITTED,
    )
    with pytest.raises(ValidationError) as exc:
        validate_leave_application(app2)
    assert "start_date" in exc.value.message_dict

    # Now test the BR-EL-012 Half-Day Exception:
    app1.delete()
    # app_hd1: First half on 2026-11-12
    LeaveApplication.objects.create(
        user_id=101,
        category=LeaveCategory.CL,
        start_date=date(2026, 11, 12),
        end_date=date(2026, 11, 12),
        half_day_slot=HalfDaySlot.FIRST_HALF,
        calculated_days=Decimal("0.5"),
        status=LeaveStatus.APPROVED,
    )

    # app_hd2: Second half on same date 2026-11-12 -> Permitted under BR-EL-012!
    app_hd2 = LeaveApplication(
        user_id=101,
        category=LeaveCategory.CL,
        start_date=date(2026, 11, 12),
        end_date=date(2026, 11, 12),
        half_day_slot=HalfDaySlot.SECOND_HALF,
        status=LeaveStatus.SUBMITTED,
    )
    # Should not raise
    validate_leave_application(app_hd2)
    assert app_hd2.calculated_days == Decimal("0.5")


@pytest.mark.django_db
def test_substitute_validation():
    # Cannot nominate self as substitute
    app = LeaveApplication(
        user_id=105,
        substitute_id=105,
        category=LeaveCategory.CL,
        start_date=date(2026, 11, 16),
        end_date=date(2026, 11, 17),
        status=LeaveStatus.SUBMITTED,
    )
    with pytest.raises(ValidationError) as exc:
        validate_leave_application(app)
    assert "substitute_id" in exc.value.message_dict
