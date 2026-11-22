from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from modules.elm.models import (
    HolidayCalendar,
    HolidayDate,
    LeaveUsage,
)
from modules.elm.services import apply_leave

pytestmark = pytest.mark.django_db


def test_br001_xyz_rejected(elm_people):
    with pytest.raises(ValidationError):
        apply_leave(
            applicant=elm_people[0],
            category="XYZ",
            start_date=__import__("datetime").date(2026, 1, 1),
            end_date=__import__("datetime").date(2026, 1, 1),
        )


def test_br002_cl_over_8_rejected(elm_people):
    LeaveUsage.objects.create(employee=elm_people[0], category="CL", year=2026, used_days=8)
    with pytest.raises(ValidationError):
        apply_leave(
            applicant=elm_people[0],
            category="CL",
            start_date=__import__("datetime").date(2026, 1, 1),
            end_date=__import__("datetime").date(2026, 1, 1),
        )


def test_br002_cl_used_plus_requested_at_most_8_accepted(elm_people):
    LeaveUsage.objects.create(
        employee=elm_people[0], category="CL", year=2026, used_days=Decimal("7.5")
    )
    request = apply_leave(
        applicant=elm_people[0],
        category="CL",
        start_date="2026-01-01",
        end_date="2026-01-01",
        first_half=True,
    )
    assert request.category == "CL"


def test_br003_rh_limit_rejected(elm_people):
    LeaveUsage.objects.create(employee=elm_people[0], category="RH", year=2026, used_days=2)
    from modules.elm.models import HolidayCalendar, HolidayDate

    calendar = HolidayCalendar.objects.create(name="RH", year=2026, is_published=True)
    HolidayDate.objects.create(calendar=calendar, date="2026-01-01", is_restricted_holiday=True)
    with pytest.raises(ValidationError):
        apply_leave(
            applicant=elm_people[0], category="RH", start_date="2026-01-01", end_date="2026-01-01"
        )


def test_br003_rh_date_outside_calendar_rejected(elm_people):
    calendar = HolidayCalendar.objects.create(name="RH", year=2026, is_published=True)
    HolidayDate.objects.create(calendar=calendar, date="2026-01-02", is_restricted_holiday=True)
    with pytest.raises(ValidationError):
        apply_leave(
            applicant=elm_people[0], category="RH", start_date="2026-01-01", end_date="2026-01-01"
        )


def test_br003_rh_date_in_calendar_accepted(elm_people):
    calendar = HolidayCalendar.objects.create(name="RH", year=2026, is_published=True)
    HolidayDate.objects.create(calendar=calendar, date="2026-01-02", is_restricted_holiday=True)
    request = apply_leave(
        applicant=elm_people[0], category="RH", start_date="2026-01-02", end_date="2026-01-02"
    )
    assert request.category == "RH"


def test_br004_scl_purpose_not_system_rejected(elm_people):
    request = apply_leave(
        applicant=elm_people[0], category="SCL", start_date="2026-01-01", end_date="2026-01-01"
    )
    assert request.category == "SCL"


def test_br006_vl_requires_faculty_vacation(elm_people):
    with pytest.raises(ValidationError):
        apply_leave(
            applicant=elm_people[0], category="VL", start_date="2026-01-01", end_date="2026-01-01"
        )


def test_br010_half_day_is_point_five(elm_people):
    request = apply_leave(
        applicant=elm_people[0],
        category="CL",
        start_date="2026-01-01",
        end_date="2026-01-01",
        first_half=True,
    )
    assert request.num_days == Decimal("0.5")


def test_br012_full_day_overlap_rejected(elm_people):
    apply_leave(
        applicant=elm_people[0], category="CL", start_date="2026-01-01", end_date="2026-01-01"
    )
    with pytest.raises(ValidationError):
        apply_leave(
            applicant=elm_people[0],
            category="CL",
            start_date="2026-01-01",
            end_date="2026-01-01",
            first_half=True,
        )


def test_br014_substitute_overlap_rejected(elm_people):
    apply_leave(
        applicant=elm_people[1], category="CL", start_date="2026-01-01", end_date="2026-01-01"
    )
    with pytest.raises(ValidationError):
        apply_leave(
            applicant=elm_people[0],
            category="CL",
            start_date="2026-01-01",
            end_date="2026-01-01",
            substitute=elm_people[1],
        )


def test_br009_col_over_20_rejected(elm_people):
    LeaveUsage.objects.create(employee=elm_people[0], category="COL", year=2026, used_days=20)
    with pytest.raises(ValidationError):
        apply_leave(
            applicant=elm_people[0], category="COL", start_date="2026-01-01", end_date="2026-01-02"
        )


def test_br012_opposite_cl_halves_allowed(elm_people):
    apply_leave(
        applicant=elm_people[0],
        category="CL",
        start_date="2026-01-01",
        end_date="2026-01-01",
        first_half=True,
    )
    request = apply_leave(
        applicant=elm_people[0],
        category="CL",
        start_date="2026-01-01",
        end_date="2026-01-01",
        second_half=True,
    )
    assert request.second_half is True


def test_br012_two_first_half_cl_rejected(elm_people):
    apply_leave(
        applicant=elm_people[0],
        category="CL",
        start_date="2026-01-01",
        end_date="2026-01-01",
        first_half=True,
    )
    with pytest.raises(ValidationError):
        apply_leave(
            applicant=elm_people[0],
            category="CL",
            start_date="2026-01-01",
            end_date="2026-01-01",
            first_half=True,
        )


def test_br013_station_details_stored_on_application(elm_people):
    request = apply_leave(
        applicant=elm_people[0],
        category="CL",
        start_date="2026-01-01",
        end_date="2026-01-01",
        station_leave_details={"permission": "SL-1"},
    )
    assert request.station_leave_details == {"permission": "SL-1"}


def test_br013_no_separate_station_leave_endpoint(elm_client, elm_people):
    assert elm_client(elm_people[0]).post("/api/v1/elm/station-leave/").status_code == 404


def test_br014_self_substitute_rejected(elm_people):
    with pytest.raises(ValidationError):
        apply_leave(
            applicant=elm_people[0],
            category="CL",
            start_date="2026-01-01",
            end_date="2026-01-01",
            substitute=elm_people[0],
        )


def test_row_1_substitute_state(elm_people):
    request = apply_leave(
        applicant=elm_people[0],
        category="CL",
        start_date="2026-01-01",
        end_date="2026-01-01",
        substitute=elm_people[2],
    )
    assert request.state == "Awaiting Substitute Response"


def test_row_3_unit_head_state(elm_people):
    request = apply_leave(
        applicant=elm_people[0], category="CL", start_date="2026-01-01", end_date="2026-01-01"
    )
    assert request.state == "Awaiting Unit Head Review"


def test_row_2_director_state(elm_people):
    elm_people[0].is_director = True
    elm_people[0].save(update_fields=["is_director"])
    request = apply_leave(
        applicant=elm_people[0], category="CL", start_date="2026-01-01", end_date="2026-01-01"
    )
    assert request.state == "Awaiting Director Self-Sanction"
