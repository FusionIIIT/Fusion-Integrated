"""Tests for Leave lifecycle (apply, validate, approve, reject, forward, balance deduction)."""
from datetime import date
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.hreis.models import EmployeeServiceRecord, LeaveRequest

pytestmark = pytest.mark.django_db


@pytest.fixture
def employee_setup():
    rec = EmployeeServiceRecord.objects.create(
        user_id=201,
        employee_id="PF-201",
        category="faculty",
        designation="Assistant Professor",
        department="CSE",
        appointment_date="2020-01-01",
        leave_balances={"casual": 4.0, "medical": 15.0},
    )
    return rec


def test_leave_application_insufficient_balance(stub_iam, user_ref, employee_setup):
    stub_iam(
        make_session(
            user_id=201,
            kind="faculty",
            roles=("faculty",),
            modules=("hr_eis",),
            permissions=("hr_eis.leave.apply", "hr_eis.leave.view_self"),
        ),
        users={201: user_ref(201, name="Prof. John", kind="faculty")},
    )

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token fake-token")

    # Asking for 5 days of casual leave when balance is 4.0
    payload = {
        "leave_type": "casual",
        "start_date": "2026-03-01",
        "end_date": "2026-03-05",
        "duration_days": 5.0,
        "justification": "Attending personal wedding",
    }
    resp = client.post("/api/v1/hreis/leaves/", payload, format="json")
    assert resp.status_code == 400
    assert "Insufficient leave balance" in str(resp.json())


def test_leave_application_and_approval_flow(stub_iam, user_ref, employee_setup):
    # 1. Apply for 2 days casual leave
    stub_iam(
        make_session(
            user_id=201,
            kind="faculty",
            roles=("faculty",),
            modules=("hr_eis",),
            permissions=("hr_eis.leave.apply", "hr_eis.leave.view_self"),
        ),
        users={201: user_ref(201, name="Prof. John", kind="faculty")},
    )

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token fake-token")

    payload = {
        "leave_type": "casual",
        "start_date": "2026-03-01",
        "end_date": "2026-03-02",
        "duration_days": 2.0,
        "justification": "Personal urgent work",
    }
    resp = client.post("/api/v1/hreis/leaves/", payload, format="json")
    assert resp.status_code == 201
    leave_id = resp.json()["id"]
    assert resp.json()["status"] == "pending"

    # 2. Approving authority (HOD) approves
    stub_iam(
        make_session(
            user_id=301,
            kind="faculty",
            roles=("hod",),
            modules=("hr_eis",),
            permissions=("hr_eis.leave.review", "hr_eis.leave.view_all"),
        ),
        users={
            201: user_ref(201, name="Prof. John", kind="faculty"),
            301: user_ref(301, name="HOD CSE", kind="faculty"),
        },
    )

    hod_client = APIClient()
    hod_client.credentials(HTTP_AUTHORIZATION="Token fake-token")

    decide_resp = hod_client.post(
        f"/api/v1/hreis/leaves/{leave_id}/decide/",
        {"outcome": "approved", "remarks": "Approved with best wishes"},
        format="json",
    )
    assert decide_resp.status_code == 200
    assert decide_resp.json()["status"] == "approved"

    # 3. Verify balance is deducted: 4.0 - 2.0 = 2.0
    employee_setup.refresh_from_db()
    assert employee_setup.leave_balances["casual"] == 2.0


def test_leave_rejection_flow(stub_iam, user_ref, employee_setup):
    leave = LeaveRequest.objects.create(
        user_id=201,
        leave_type="casual",
        start_date="2026-04-01",
        end_date="2026-04-02",
        duration_days=2.0,
        justification="Short break",
        status="pending",
    )

    # Authority rejects
    stub_iam(
        make_session(
            user_id=301,
            kind="faculty",
            roles=("hod",),
            modules=("hr_eis",),
            permissions=("hr_eis.leave.review", "hr_eis.leave.view_all"),
        ),
        users={
            201: user_ref(201, name="Prof. John", kind="faculty"),
            301: user_ref(301, name="HOD CSE", kind="faculty"),
        },
    )

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token fake-token")

    resp = client.post(
        f"/api/v1/hreis/leaves/{leave.id}/decide/",
        {"outcome": "rejected", "remarks": "Project deadlines pending"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"

    # Verify balance was NOT deducted
    employee_setup.refresh_from_db()
    assert employee_setup.leave_balances["casual"] == 4.0
