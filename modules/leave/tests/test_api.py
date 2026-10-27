"""API endpoint tests for Leave Management."""
import datetime
from decimal import Decimal
import pytest
from rest_framework.test import APIClient

from modules.leave.models import LeaveBalance, LeaveApplication


from conftest import make_session


@pytest.fixture
def auth_client(stub_iam):
    def _create(user_id=1, kind="staff", permissions=("leave.application.view_self", "leave.application.create")):
        stub_iam(make_session(user_id=user_id, kind=kind, modules=("leave",), permissions=permissions))
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION="Token test-token")
        return c
    return _create


@pytest.mark.django_db
def test_balances_endpoint(auth_client):
    client = auth_client(user_id=1)
    LeaveBalance.objects.create(user_id=1, year=2026, cl_balance=Decimal("8.0"))
    resp = client.get("/api/v1/leave/balances/?year=2026")
    assert resp.status_code == 200
    assert "balance" in resp.data
    assert resp.data["balance"]["cl_balance"] == "8.0"


@pytest.mark.django_db
def test_apply_leave_endpoint(auth_client):
    client = auth_client(user_id=1)
    LeaveBalance.objects.create(user_id=1, year=2026, cl_balance=Decimal("8.0"))
    payload = {
        "category": "CL",
        "start_date": "2026-11-02",
        "end_date": "2026-11-03",
        "purpose": "Personal errand",
        "half_day_type": "full",
    }
    resp = client.post("/api/v1/leave/applications/", data=payload, format="json")
    assert resp.status_code == 201
    assert resp.data["category"] == "CL"
    assert resp.data["days_count"] == "2.0"


@pytest.mark.django_db
def test_my_applications_and_export_endpoint(auth_client):
    client = auth_client(user_id=1)
    LeaveBalance.objects.create(user_id=1, year=2026, cl_balance=Decimal("8.0"))
    payload = {
        "category": "CL",
        "start_date": "2026-11-02",
        "end_date": "2026-11-03",
        "purpose": "Export test",
    }
    resp = client.post("/api/v1/leave/applications/", data=payload, format="json")
    app_id = resp.data["id"]

    # List my applications
    list_resp = client.get("/api/v1/leave/applications/")
    assert list_resp.status_code == 200
    assert len(list_resp.data) >= 1

    # Export CSV representation
    exp_resp = client.get(f"/api/v1/leave/applications/{app_id}/export/")
    assert exp_resp.status_code == 200
    assert "text/csv" in exp_resp["Content-Type"]


@pytest.mark.django_db
def test_substitute_respond_endpoint(auth_client):
    from modules.leave.models import SubstituteRequest
    # Create application with substitute user 2
    LeaveBalance.objects.create(user_id=1, year=2026, cl_balance=Decimal("8.0"))
    app = LeaveApplication.objects.create(
        user_id=1, category="CL", start_date=datetime.date(2026, 11, 2),
        end_date=datetime.date(2026, 11, 3), days_count=Decimal("2.0"),
        purpose="Substitute test", status="substitute_pending",
    )
    sub_req = SubstituteRequest.objects.create(
        application=app, substitute_user_id=2, status="pending", responsibilities="Cover classes",
    )

    client = auth_client(user_id=2, permissions=("leave.substitute.respond",))
    resp = client.post(
        f"/api/v1/leave/substitutes/{sub_req.pk}/respond/",
        data={"decision": "accepted", "remarks": "Sure, will cover"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "accepted"
    app.refresh_from_db()
    assert app.status == "under_review"


@pytest.mark.django_db
def test_approvals_queue_and_unit_head_decision(auth_client):
    LeaveBalance.objects.create(user_id=1, year=2026, cl_balance=Decimal("8.0"))
    app = LeaveApplication.objects.create(
        user_id=1, category="CL", start_date=datetime.date(2026, 11, 2),
        end_date=datetime.date(2026, 11, 3), days_count=Decimal("2.0"),
        purpose="Review test", status="under_review", unit_head_user_id=201,
    )

    # Unit head inspects queue
    client = auth_client(user_id=201, permissions=("leave.application.review",))
    queue_resp = client.get("/api/v1/leave/approvals/")
    assert queue_resp.status_code == 200
    assert any(item["id"] == app.pk for item in queue_resp.data)

    # Unit head approves CL
    review_resp = client.post(
        f"/api/v1/leave/approvals/{app.pk}/unit-head-review/",
        data={"recommended": True, "remarks": "Approved by HOD"},
        format="json",
    )
    assert review_resp.status_code == 200
    assert review_resp.data["status"] == "approved"


@pytest.mark.django_db
def test_calendar_and_admin_policy_endpoints(auth_client):
    from modules.leave.models import HolidayCalendar
    HolidayCalendar.objects.create(
        name="Independence Day", date=datetime.date(2026, 8, 15), kind="closed",
        year=2026, is_published=True,
    )

    client = auth_client(user_id=1, permissions=("leave.calendar.view", "leave.admin.manage"))
    cal_resp = client.get("/api/v1/leave/calendar/?year=2026")
    assert cal_resp.status_code == 200
    assert len(cal_resp.data["holidays"]) >= 1

    # Admin updates policy parameter
    policy_resp = client.post(
        "/api/v1/leave/admin/config/",
        data={"key": "sla.reminder_hours", "value": {"hours": 12}, "description": "Custom SLA"},
        format="json",
    )
    assert policy_resp.status_code == 200
    assert policy_resp.data["status"] == "updated"
