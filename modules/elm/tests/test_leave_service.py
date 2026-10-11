"""Integration tests for ELM services, selectors, and cross-module contracts."""

from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from rest_framework.exceptions import PermissionDenied, ValidationError

from modules.elm.contracts import get_employee_leave_profiles
from modules.elm.models import LeaveBalance
from modules.elm.selectors.queries import list_approval_queue, list_employee_applications
from modules.elm.services.leave import (
    allot_balance,
    cancel_approved,
    decide,
    submit,
    upsert_holiday,
    upsert_profile,
    withdraw,
)


def _principal(user_id: int) -> SimpleNamespace:
    return SimpleNamespace(user_id=user_id)


@pytest.mark.django_db
def test_cl_submission_and_unit_head_final_approval():
    upsert_profile(
        {
            "user_id": 101,
            "category": "staff",
            "designation": "Senior Assistant",
            "unit": "Establishment",
            "unit_head_user_id": 201,
            "sanction_authority_user_id": 301,
        }
    )
    allot_balance(
        {"employee_id": 101, "category": "CL", "year": 2026, "allotted": Decimal("8.0")}
    )
    app = submit(
        _principal(101),
        {
            "category": "CL",
            "start_date": date(2026, 10, 12),
            "end_date": date(2026, 10, 12),
            "half_day": "FIRST",
            "reason": "Personal work",
        },
    )
    assert app.status == "PENDING"
    assert app.duration == Decimal("0.5")
    with pytest.raises(PermissionDenied):
        decide(_principal(101), app.id, action="approve")
    decided = decide(_principal(201), app.id, action="approve", remarks="Approved")
    assert decided.status == "APPROVED"
    bal = LeaveBalance.objects.get(employee_id=101, year=2026, category="CL")
    assert bal.used == Decimal("0.5")


@pytest.mark.django_db
def test_el_substitute_recommendation_and_higher_sanction():
    upsert_profile(
        {
            "user_id": 102,
            "category": "faculty",
            "designation": "Assistant Professor",
            "unit": "CSE",
            "unit_head_user_id": 202,
            "sanction_authority_user_id": 302,
        }
    )
    allot_balance(
        {"employee_id": 102, "category": "EL", "year": 2026, "allotted": Decimal("30.0")}
    )
    app = submit(
        _principal(102),
        {
            "category": "EL",
            "start_date": date(2026, 11, 2),
            "end_date": date(2026, 11, 4),
            "reason": "Family event",
            "station_leave": True,
            "station_location": "Delhi",
            "substitute_user_id": 103,
        },
    )
    assert app.status == "AWAITING_SUB"
    assert list(list_approval_queue(103)) == [app]
    sub_ok = decide(_principal(103), app.id, action="accept_substitute", remarks="Will cover")
    assert sub_ok.status == "PENDING"
    rec = decide(_principal(202), app.id, action="recommend", remarks="Forwarded")
    assert rec.status == "RECOMMENDED"
    assert rec.recommendation == "RECOMMENDED"
    final = decide(_principal(302), app.id, action="approve", remarks="Sanctioned")
    assert final.status == "APPROVED"
    bal = LeaveBalance.objects.get(employee_id=102, year=2026, category="EL")
    assert bal.used == Decimal("3.0")


@pytest.mark.django_db
def test_withdrawal_and_pre_start_cancellation():
    upsert_profile(
        {
            "user_id": 104,
            "category": "faculty",
            "designation": "Associate Professor",
            "unit": "ECE",
            "unit_head_user_id": 204,
            "sanction_authority_user_id": 304,
        }
    )
    future_day = date.today() + timedelta(days=30)
    while future_day.weekday() >= 5:
        future_day += timedelta(days=1)
    allot_balance(
        {
            "employee_id": 104,
            "category": "RH",
            "year": future_day.year,
            "allotted": Decimal("2.0"),
        }
    )
    upsert_holiday({"date": future_day, "name": "Festival RH", "kind": "RH", "published": True})
    pending = submit(
        _principal(104),
        {
            "category": "RH",
            "start_date": future_day,
            "end_date": future_day,
            "reason": "Observance",
        },
    )
    withdrawn = withdraw(_principal(104), pending.id)
    assert withdrawn.status == "WITHDRAWN"

    second = submit(
        _principal(104),
        {
            "category": "RH",
            "start_date": future_day,
            "end_date": future_day,
            "reason": "Re-applied",
        },
    )
    decide(_principal(204), second.id, action="approve")
    cancelled = cancel_approved(_principal(104), second.id, remarks="Plans changed")
    assert cancelled.status == "CANCELLED"
    bal = LeaveBalance.objects.get(employee_id=104, year=future_day.year, category="RH")
    assert bal.used == Decimal("0.0")
    assert len(list_employee_applications(104)) == 2
    assert get_employee_leave_profiles([104])[0]["unit"] == "ECE"


@pytest.mark.django_db
def test_validation_guards_station_leave_and_overlap():
    upsert_profile(
        {
            "user_id": 105,
            "category": "staff",
            "designation": "Clerk",
            "unit": "Admin",
            "unit_head_user_id": 205,
            "sanction_authority_user_id": 305,
        }
    )
    allot_balance(
        {"employee_id": 105, "category": "CL", "year": 2026, "allotted": Decimal("8.0")}
    )
    with pytest.raises(ValidationError):
        submit(
            _principal(105),
            {
                "category": "CL",
                "start_date": date(2026, 10, 12),
                "end_date": date(2026, 10, 12),
                "reason": "Trip",
                "station_leave": True,
                "station_location": "",
            },
        )
    submit(
        _principal(105),
        {
            "category": "CL",
            "start_date": date(2026, 10, 12),
            "end_date": date(2026, 10, 13),
            "reason": "First request",
        },
    )
    with pytest.raises(ValidationError):
        submit(
            _principal(105),
            {
                "category": "CL",
                "start_date": date(2026, 10, 13),
                "end_date": date(2026, 10, 14),
                "reason": "Overlapping request",
            },
        )
