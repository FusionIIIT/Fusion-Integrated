import pytest
from datetime import date
from modules.hreis.models import EmployeeServiceRecord, LeaveRequest

pytestmark = pytest.mark.django_db


def test_fr_010_employee_submit_hr_request(auth_client_factory):
    """TEST-FR-010 [HR-AFR-002]: Verify HR-EIS allows an Employee to submit HR-related requests."""
    EmployeeServiceRecord.objects.create(
        user_id=120,
        employee_id="EMP0120",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 8},
    )
    client, _ = auth_client_factory(user_id=120, role="faculty")
    payload = {
        "leave_type": "casual",
        "start_date": "2026-11-20",
        "end_date": "2026-11-21",
        "duration_days": 2,
        "justification": "Attending symposium",
    }
    resp = client.post("/api/v1/hreis/leaves/", payload, format="json")
    assert resp.status_code == 201
    assert resp.data["status"] == "pending"


def test_fr_011_employee_track_request_statuses(auth_client_factory):
    """TEST-FR-011 [HR-AFR-004]: Verify HR-EIS allows an Employee to track statuses of HR-related requests submitted by the Employee."""
    EmployeeServiceRecord.objects.create(
        user_id=121,
        employee_id="EMP0121",
        department="ECE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 10},
    )
    LeaveRequest.objects.create(
        user_id=121,
        leave_type="casual",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 2),
        duration_days=2,
        justification="Personal work",
        status="pending",
        current_authority_role="hod",
    )
    client, _ = auth_client_factory(user_id=121, role="faculty")
    resp = client.get("/api/v1/hreis/leaves/")
    assert resp.status_code == 200
    results = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
    assert len(results) >= 1
    assert results[0]["status"] == "pending"
