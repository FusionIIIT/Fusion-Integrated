"""API endpoint tests for Leave Management."""
import datetime
from decimal import Decimal
import pytest
from rest_framework.test import APIClient

from modules.leave.models import LeaveBalance, LeaveApplication


@pytest.fixture
def client():
    return APIClient()


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
