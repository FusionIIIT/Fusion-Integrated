from datetime import date
from decimal import Decimal

import pytest

from modules.leave.models import LeaveRequest

pytestmark = pytest.mark.django_db
URL = "/api/v1/leave"


@pytest.fixture
def leave_requests(unit):
    return [
        LeaveRequest.objects.create(
            user_id=101,
            category="EL",
            start_date=date(2030, 3, 4),
            end_date=date(2030, 3, 8),
            days=Decimal("5"),
            purpose="x",
            unit=unit,
            status="routing",
            substitute_status="not_required",
        ),
        LeaveRequest.objects.create(
            user_id=101,
            category="EL",
            start_date=date(2030, 3, 4),
            end_date=date(2030, 3, 8),
            days=Decimal("5"),
            purpose="x",
            unit=unit,
            status="sanctioned",
            substitute_status="not_required",
        ),
        LeaveRequest.objects.create(
            user_id=202,
            category="EL",
            start_date=date(2030, 3, 4),
            end_date=date(2030, 3, 8),
            days=Decimal("5"),
            purpose="x",
            unit=unit,
            status="routing",
            substitute_status="not_required",
        ),
    ]


def test_employee_sees_own_request_only(as_user, leave_requests):
    """BR-EL-036: test_employee_sees_own_request_only"""
    client = as_user(101, "leave.request.view_self")
    r = client.get(f"{URL}/requests")
    assert {x["id"] for x in r.json()["results"]} == {
        q.id for q in leave_requests if q.user_id == 101
    }


def test_router_sees_routing_requests(as_user, leave_requests):
    """BR-EL-036: test_router_sees_routing_requests"""
    client = as_user(600, "leave.request.route")
    r = client.get(f"{URL}/requests")
    assert {q.id for q in leave_requests if q.status == "routing"} <= {
        x["id"] for x in r.json()["results"]
    }


def test_unit_head_sees_unit_requests(as_user, leave_requests):
    """BR-EL-036: test_unit_head_sees_unit_requests"""
    client = as_user(500, "leave.request.review")
    r = client.get(f"{URL}/requests")
    assert {q.id for q in leave_requests if q.unit.unit_head_user_id == 500} == {
        x["id"] for x in r.json()["results"]
    }


def test_unrelated_reviewer_sees_nothing(as_user, leave_requests):
    """BR-EL-036: test_unrelated_reviewer_sees_nothing"""
    client = as_user(999, "leave.request.review")
    r = client.get(f"{URL}/requests")
    assert not r.json()["results"]
