from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from rest_framework.exceptions import ValidationError

from modules.leave_elm.models import (
    HolidayCalendar,
    LeaveApplication,
    LeaveBalance,
    LeaveCategory,
    PolicyConfiguration,
)
from modules.leave_elm.services import (
    chargeable_days,
    review_application,
    submit_application,
    validate_application,
)


@pytest.mark.django_db
def test_noncontinuous_leave_excludes_published_closed_holidays():
    category = LeaveCategory.objects.create(code="CL", name="Casual Leave")
    HolidayCalendar.objects.create(
        name="2026", year=2026, holidays=["2026-10-27"], is_published=True
    )

    days = chargeable_days(category, date(2026, 10, 26), date(2026, 10, 28))

    assert days == Decimal("2")


@pytest.mark.django_db
def test_half_day_must_be_single_day_casual_leave():
    category = LeaveCategory.objects.create(code="CL", name="Casual Leave")
    LeaveBalance.objects.create(
        user_id=10, category=category, year=2026, closing_balance=Decimal("8")
    )

    with pytest.raises(ValidationError):
        validate_application(
            user_id=10,
            category=category,
            starts_on=date(2026, 10, 26),
            ends_on=date(2026, 10, 27),
            half_day="first",
        )


@pytest.mark.django_db
def test_restricted_holiday_must_be_in_published_calendar():
    category = LeaveCategory.objects.create(code="RH", name="Restricted Holiday")
    LeaveBalance.objects.create(
        user_id=10, category=category, year=2026, closing_balance=Decimal("2")
    )
    HolidayCalendar.objects.create(
        name="2026", year=2026, restricted_holidays=["2026-10-26"], is_published=True
    )

    with pytest.raises(ValidationError):
        validate_application(
            user_id=10,
            category=category,
            starts_on=date(2026, 10, 27),
            ends_on=date(2026, 10, 27),
            half_day="full",
        )


@pytest.mark.django_db
def test_non_unit_head_cannot_decide_cl_request():
    category = LeaveCategory.objects.create(code="CL", name="Casual Leave")
    application = LeaveApplication.objects.create(
        user_id=10,
        category=category,
        starts_on=date(2026, 10, 26),
        ends_on=date(2026, 10, 26),
        requested_days=Decimal("1"),
        purpose="Personal",
        status="awaiting_unit_head",
        assigned_role="unit_head",
    )
    actor = SimpleNamespace(user_id=11, active_role="registrar", roles=("registrar",))

    with pytest.raises(ValidationError):
        review_application(application=application, actor=actor, outcome="approved")


@pytest.mark.django_db
def test_unit_head_recommendation_routes_to_configured_authority():
    category = LeaveCategory.objects.create(code="SCL", name="Special Casual Leave")
    PolicyConfiguration.objects.create(
        category=category, key="hierarchy", value={"sanctioning_roles": ["dean"]}
    )
    application = LeaveApplication.objects.create(
        user_id=10,
        category=category,
        starts_on=date(2026, 10, 26),
        ends_on=date(2026, 10, 26),
        requested_days=Decimal("1"),
        purpose="Conference",
        status="awaiting_unit_head",
        assigned_role="unit_head",
    )
    actor = SimpleNamespace(user_id=11, active_role="unit_head", roles=("unit_head",))

    review_application(application=application, actor=actor, outcome="recommended")
    application.refresh_from_db()

    assert application.status == "awaiting_sanction"
    assert application.assigned_role == "dean"


@pytest.mark.django_db
def test_continuous_leave_allocates_days_to_each_calendar_year():
    category = LeaveCategory.objects.create(code="EL", name="Earned Leave")

    from modules.leave_elm.services import chargeable_days_by_year

    allocation = chargeable_days_by_year(category, date(2026, 12, 31), date(2027, 1, 2))

    assert allocation == {2026: Decimal("1"), 2027: Decimal("2")}


@pytest.mark.django_db
def test_vl_requires_faculty_role_and_configured_vacation_period():
    category = LeaveCategory.objects.create(code="VL", name="Vacation Leave")
    LeaveBalance.objects.create(
        user_id=10, category=category, year=2026, closing_balance=Decimal("60")
    )
    PolicyConfiguration.objects.create(
        key="academic_vacation_periods",
        value=[{"starts_on": "2026-06-01", "ends_on": "2026-07-15"}],
    )

    validate_application(
        user_id=10,
        category=category,
        starts_on=date(2026, 6, 5),
        ends_on=date(2026, 6, 6),
        half_day="full",
        applicant_role="faculty",
    )
    with pytest.raises(ValidationError):
        validate_application(
            user_id=10,
            category=category,
            starts_on=date(2026, 6, 5),
            ends_on=date(2026, 6, 6),
            half_day="full",
            applicant_role="staff",
        )
    with pytest.raises(ValidationError):
        validate_application(
            user_id=10,
            category=category,
            starts_on=date(2026, 8, 5),
            ends_on=date(2026, 8, 6),
            half_day="full",
            applicant_role="faculty",
        )


@pytest.mark.django_db
def test_submit_application_persists_requested_days_by_year():
    category = LeaveCategory.objects.create(code="EL", name="Earned Leave")
    LeaveBalance.objects.create(
        user_id=10, category=category, year=2026, closing_balance=Decimal("10")
    )

    application = submit_application(
        user_id=10,
        category_id=category.pk,
        starts_on=date(2026, 10, 26),
        ends_on=date(2026, 10, 27),
        half_day="full",
        purpose="Personal",
        station_leave=False,
        station_destination="",
        applicant_role="staff",
    )

    assert application.requested_days == Decimal("2")
    assert application.requested_days_by_year == {"2026": "2"}
