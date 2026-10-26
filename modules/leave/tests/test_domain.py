from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.utils import timezone

from modules.leave.models import HolidayCalendar, LeaveAccount, LeaveApplication, LeavePolicy
from modules.leave.services import extension, validate_application
from modules.leave.domain import LeaveRuleError, chargeable_days, conversion_vl_to_el, overlaps


def test_continuous_categories_include_weekends_and_holidays():
    assert chargeable_days(
        "EL", date(2026, 1, 2), date(2026, 1, 5), closed_holidays=(date(2026, 1, 5),)
    ) == Decimal("4")


def test_non_continuous_categories_exclude_weekends_and_closed_holidays():
    assert chargeable_days(
        "CL", date(2026, 1, 2), date(2026, 1, 5), closed_holidays=(date(2026, 1, 5),)
    ) == Decimal("1")


def test_half_day_cl_and_same_day_different_halves():
    assert chargeable_days("CL", date(2026, 1, 5), date(2026, 1, 5), half="first") == Decimal("0.5")
    assert not overlaps(
        date(2026, 1, 5),
        date(2026, 1, 5),
        "CL",
        "first",
        date(2026, 1, 5),
        date(2026, 1, 5),
        "CL",
        "second",
    )


def test_vl_conversion_preserves_fraction():
    assert conversion_vl_to_el(Decimal("5.5")) == Decimal("2.75")


def test_invalid_interval_is_rejected():
    with pytest.raises(LeaveRuleError):
        chargeable_days("EL", date(2026, 1, 6), date(2026, 1, 5))


@pytest.mark.django_db
def test_rh_request_must_cover_only_valid_restricted_holiday_dates():
    HolidayCalendar.objects.create(
        year=2026,
        version=1,
        published=True,
        holidays=[{"date": "2026-01-03", "kind": "RH"}],
        published_at=timezone.now(),
    )
    LeavePolicy.objects.create(year=2026, values={"entitlements": {"RH": 2}})

    actor = SimpleNamespace(user_id=7, kind="staff", roles=())

    with pytest.raises(LeaveRuleError, match="RH"):
        validate_application(
            actor=actor,
            category="RH",
            start_date=date(2026, 1, 3),
            end_date=date(2026, 1, 4),
        )


@pytest.mark.django_db
def test_rh_half_day_requests_are_rejected():
    HolidayCalendar.objects.create(
        year=2026,
        version=1,
        published=True,
        holidays=[{"date": "2026-01-03", "kind": "RH"}],
        published_at=timezone.now(),
    )
    LeavePolicy.objects.create(year=2026, values={"entitlements": {"RH": 2}})

    actor = SimpleNamespace(user_id=7, kind="staff", roles=())

    with pytest.raises(LeaveRuleError, match="CL"):
        validate_application(
            actor=actor,
            category="RH",
            start_date=date(2026, 1, 3),
            end_date=date(2026, 1, 3),
            half="first",
        )


@pytest.mark.django_db
def test_extension_preserves_approval_assignments():
    LeavePolicy.objects.create(year=2026, values={"entitlements": {"EL": 30}})
    LeaveAccount.objects.create(user_id=7, year=2026, category="EL", balance=Decimal("30"))
    app = LeaveApplication.objects.create(
        user_id=7,
        category="EL",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        purpose="Approved leave",
        chargeable_days=Decimal("365"),
        state="approved",
        unit_head_user_id=11,
        final_authority_user_id=12,
        route={"establishment_user_id": 13},
    )
    actor = SimpleNamespace(user_id=7, kind="staff", roles=())

    request = extension(
        actor=actor,
        app=app,
        start_date=date(2026, 10, 12),
        end_date=date(2026, 10, 13),
        purpose="Extension",
    )

    assert request.unit_head_user_id == 11
    assert request.final_authority_user_id == 12
    assert request.route["establishment_user_id"] == 13
