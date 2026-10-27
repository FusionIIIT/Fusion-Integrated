from datetime import date
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.leave.models import LeaveApplication, LeaveBalance, LeaveType
from modules.leave.services import submit_leave_application

pytestmark = pytest.mark.django_db


def test_leave_type_and_balance_creation():
    lt = LeaveType.objects.create(name="Casual Leave", description="Casual leaves")
    assert lt.name == "Casual Leave"

    lb = LeaveBalance.objects.create(user_id=1001, leave_type=lt, balance=8)
    assert lb.balance == 8
    assert lb.user_id == 1001


def test_submit_leave_application_service():
    lt = LeaveType.objects.create(name="Earned Leave", description="Earned leaves")
    app = submit_leave_application(
        user=1002,
        leave_type=lt,
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 5),
    )
    assert app.id is not None
    assert app.user_id == 1002
    assert app.status == "pending"


def test_leave_api_endpoints(stub_iam):
    session = make_session(user_id=1003, permissions=(), modules=("leave",))
    stub_iam(session=session)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")

    lt = LeaveType.objects.create(name="Medical Leave", description="Medical leaves")
    LeaveBalance.objects.create(user_id=1003, leave_type=lt, balance=15)

    # 1. GET leave types
    res = client.get("/api/v1/leave/types/")
    assert res.status_code == 200
    results = res.json().get("results", res.json())
    assert len(results) >= 1

    # 2. GET leave balances
    res = client.get("/api/v1/leave/balances/")
    assert res.status_code == 200
    results = res.json().get("results", res.json())
    assert len(results) == 1

    # 3. POST leave application
    res = client.post("/api/v1/leave/applications/", {
        "leave_type": lt.id,
        "start_date": "2026-12-01",
        "end_date": "2026-12-03",
    })
    assert res.status_code == 201
    assert res.json()["status"] == "pending"

    # 4. GET leave applications
    res = client.get("/api/v1/leave/applications/")
    assert res.status_code == 200
    results = res.json().get("results", res.json())
    assert len(results) == 1
