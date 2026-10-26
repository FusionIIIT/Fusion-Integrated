from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from modules.elm.models import (
    HolidayCalendar,
    HolidayDate,
    LeaveApplication,
    LeavePolicy,
    LeaveUsage,
    SanctioningAuthorityRule,
)
from modules.elm.services import apply_leave, review_leave

pytestmark = pytest.mark.django_db


def request(employee, category="CL", **kwargs):
    return apply_leave(
        applicant=employee,
        category=category,
        start_date="2026-01-02",
        end_date="2026-01-02",
        **kwargs,
    )


@pytest.mark.parametrize("category,limit", [("CL", 8), ("RH", 2), ("SCL", 15), ("COL", 20)])
def test_entitlement_used_at_limit_rejected(elm_people, category, limit):
    if category == "RH":
        calendar = HolidayCalendar.objects.create(name="RH", year=2026, is_published=True)
        HolidayDate.objects.create(calendar=calendar, date="2026-01-02", is_restricted_holiday=True)
    LeaveUsage.objects.create(employee=elm_people[0], category=category, year=2026, used_days=limit)
    with pytest.raises(ValidationError, match="entitlement"):
        request(elm_people[0], category)


def test_br005_non_faculty_el_30_days_available(elm_people):
    request = apply_leave(
        applicant=elm_people[0],
        category="EL",
        start_date="2026-01-01",
        end_date="2026-01-30",
    )
    assert request.num_days == Decimal("30")


def test_br005_non_faculty_el_over_30_rejected_without_usage(elm_people):
    with pytest.raises(ValidationError, match="entitlement"):
        apply_leave(
            applicant=elm_people[0],
            category="EL",
            start_date="2026-01-01",
            end_date="2026-01-31",
        )


def test_br009_col_over_20_rejected_without_usage(elm_people):
    with pytest.raises(ValidationError, match="entitlement"):
        apply_leave(
            applicant=elm_people[0],
            category="COL",
            start_date="2026-01-01",
            end_date="2026-01-21",
        )


def test_br006_faculty_vl_60_days_available(elm_people):
    calendar = HolidayCalendar.objects.create(name="Vacation", year=2026, is_published=True)
    start = date(2026, 1, 1)
    HolidayDate.objects.bulk_create(
        [
            HolidayDate(
                calendar=calendar, date=start + timedelta(days=offset), is_vacation_period=True
            )
            for offset in range(60)
        ]
    )
    app = apply_leave(
        applicant=elm_people[4],
        category="VL",
        start_date=start,
        end_date=start + timedelta(days=59),
    )
    assert app.num_days == Decimal("60")


def test_br006_faculty_vl_over_60_rejected(elm_people):
    calendar = HolidayCalendar.objects.create(name="Vacation", year=2026, is_published=True)
    HolidayDate.objects.create(calendar=calendar, date="2026-01-02", is_vacation_period=True)
    LeaveUsage.objects.create(employee=elm_people[4], category="VL", year=2026, used_days=60)
    with pytest.raises(ValidationError, match="entitlement"):
        request(elm_people[4], "VL")


def test_br006_faculty_outside_vacation_rejected(elm_people):
    with pytest.raises(ValidationError, match="vacation"):
        request(elm_people[4], "VL")


def test_br031_draft_calendar_cannot_authorize_vl(elm_people):
    calendar = HolidayCalendar.objects.create(name="Draft vacation", year=2026, is_published=False)
    HolidayDate.objects.create(calendar=calendar, date="2026-01-02", is_vacation_period=True)
    with pytest.raises(ValidationError, match="vacation"):
        request(elm_people[4], "VL")


@pytest.mark.parametrize("first,second", [(True, False), (False, True)])
def test_br010_both_cl_halves_consume_half(elm_people, first, second):
    app = request(elm_people[0], first_half=first, second_half=second)
    review_leave(application=app, unit_head=elm_people[1], decision="Approve")
    assert LeaveUsage.objects.get(employee=elm_people[0], category="CL").used_days == Decimal("0.5")


def test_br010_full_day_cl_consumes_one(elm_people):
    app = request(elm_people[0])
    review_leave(application=app, unit_head=elm_people[1], decision="Approve")
    assert LeaveUsage.objects.get(employee=elm_people[0], category="CL").used_days == Decimal("1")


def test_br012_full_day_on_existing_half_rejected(elm_people):
    request(elm_people[0], first_half=True)
    with pytest.raises(ValidationError, match="overlap"):
        request(elm_people[0])


@pytest.mark.parametrize("existing_state", ["Awaiting Unit Head Review", "Approved"])
def test_br014_substitute_cannot_have_pending_or_approved_leave(elm_people, existing_state):
    LeaveApplication.objects.create(
        applicant=elm_people[2],
        category="CL",
        start_date="2026-01-02",
        end_date="2026-01-02",
        num_days=1,
        state=existing_state,
    )
    with pytest.raises(ValidationError, match="Substitute"):
        request(elm_people[0], substitute=elm_people[2])


def test_br004_scl_purpose_is_left_to_authority(elm_people):
    app = request(elm_people[0], "SCL", remarks="Purpose requiring authority judgment")
    SanctioningAuthorityRule.objects.create(category="SCL", authority=elm_people[3])
    review_leave(application=app, unit_head=elm_people[1], decision="Not Recommended")
    assert app.state == "Awaiting Final Sanction Decision"
    assert app.remarks == "Purpose requiring authority judgment"


@pytest.mark.parametrize("category", ["SCL", "EL", "COL", "VL"])
@pytest.mark.parametrize("decision", ["Approve", "Reject"])
def test_br017_unit_head_cannot_finally_decide_higher_categories(elm_people, category, decision):
    app = LeaveApplication.objects.create(
        applicant=elm_people[0],
        category=category,
        start_date="2026-01-02",
        end_date="2026-01-02",
        num_days=1,
        unit_head=elm_people[1],
        state="Awaiting Unit Head Review",
    )
    with pytest.raises(ValidationError):
        review_leave(application=app, unit_head=elm_people[1], decision=decision)
    app.refresh_from_db()
    assert app.state == "Awaiting Unit Head Review"


@pytest.mark.parametrize("category", ["CL", "RH"])
@pytest.mark.parametrize("decision", ["Recommended", "Not Recommended"])
def test_br016_cl_rh_cannot_enter_higher_path(elm_people, category, decision):
    app = LeaveApplication.objects.create(
        applicant=elm_people[0],
        category=category,
        start_date="2026-01-02",
        end_date="2026-01-02",
        num_days=1,
        unit_head=elm_people[1],
        state="Awaiting Unit Head Review",
    )
    with pytest.raises(ValidationError):
        review_leave(application=app, unit_head=elm_people[1], decision=decision)


def test_approval_rechecks_entitlement_without_partial_state_change(elm_people):
    first = request(elm_people[0])
    second = apply_leave(
        applicant=elm_people[0],
        category="CL",
        start_date="2026-01-05",
        end_date="2026-01-05",
    )
    LeavePolicy.objects.create(name="Current", cl_days=1)
    review_leave(application=first, unit_head=elm_people[1], decision="Approve")
    with pytest.raises(ValidationError, match="entitlement"):
        review_leave(application=second, unit_head=elm_people[1], decision="Approve")
    second.refresh_from_db()
    assert second.state == "Awaiting Unit Head Review"
    assert LeaveUsage.objects.get(employee=elm_people[0], category="CL").used_days == Decimal("1")
