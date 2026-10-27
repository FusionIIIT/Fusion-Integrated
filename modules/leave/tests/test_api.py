"""API endpoint tests for Leave Management."""
from decimal import Decimal
import pytest
from rest_framework.test import APIClient
from fusion_auth.client import IamSession

from modules.leave.models import LeaveBalance, LeavePolicyConfig


@pytest.fixture
def client(stub_iam):
    # Protected endpoints require both the Fusion module grant and permission.
    stub_iam(IamSession(
        user_id=1, username="u1", display_name="Test Employee", kind="staff",
        active_role="staff", roles=("staff",),
        permissions=frozenset({"leave.application.view_self", "leave.application.create"}),
        modules=("leave",),
    ))
    api_client = APIClient()
    api_client.credentials(HTTP_AUTHORIZATION="Token test-token")
    return api_client


@pytest.mark.django_db
def test_balances_endpoint(client):
    LeaveBalance.objects.create(user_id=1, year=2026, cl_balance=Decimal("8.0"))
    resp = client.get("/api/v1/leave/balances/?year=2026")
    assert resp.status_code == 200
    assert "balance" in resp.data
    assert resp.data["balance"]["cl_balance"] == "8.0"


@pytest.mark.django_db
def test_apply_leave_endpoint(client):
    LeaveBalance.objects.create(user_id=1, year=2026, cl_balance=Decimal("8.0"))
    LeavePolicyConfig.objects.create(
        key="route.CL", value={"unit_head_user_id": 201},
        description="Test route for the CL API integration test",
    )
    payload = {"category":"CL", "start_date":"2026-11-02", "end_date":"2026-11-03", "purpose":"Personal errand", "half_day_type":"full"}
    resp = client.post("/api/v1/leave/applications/", data=payload, format="json")
    assert resp.status_code == 201
    assert resp.data["category"] == "CL"
    assert resp.data["days_count"] == "2.0"


@pytest.mark.django_db
def test_balances_endpoint_rejects_anonymous_user():
    resp = APIClient().get("/api/v1/leave/balances/?year=2026")
    assert resp.status_code == 401
