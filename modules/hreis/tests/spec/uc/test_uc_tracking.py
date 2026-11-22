from datetime import date

import pytest
from rest_framework import status

from modules.hreis.models import EmployeeServiceRecord, LeaveRequest

pytestmark = pytest.mark.django_db


def test_uc_014_employee_track_own_submitted_request(auth_client_factory):
    """TEST-UC-014 [HR-UC-005 Main Flow]: Verify employee can track current status of their own submitted HR requests."""
    EmployeeServiceRecord.objects.create(
        user_id=220,
        employee_id="EMP0220",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 5},
    )
    leave = LeaveRequest.objects.create(
        user_id=220,
        leave_type="casual",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 2),
        duration_days=2,
        justification="Personal work",
        status="pending",
        current_authority_role="hod",
    )
    client, _ = auth_client_factory(user_id=220, role="faculty")
    resp = client.get("/api/v1/hreis/leaves/")
    assert resp.status_code == status.HTTP_200_OK
    results = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
    assert any(r["id"] == leave.id and r["status"] == "pending" for r in results)


def test_uc_015_employee_track_no_requests(auth_client_factory):
    """TEST-UC-015 [HR-UC-005 Alternative A1]: Verify employee tracking with no submitted requests receives empty result gracefully."""
    EmployeeServiceRecord.objects.create(
        user_id=221,
        employee_id="EMP0221",
        department="ECE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 5},
    )
    client, _ = auth_client_factory(user_id=221, role="faculty")
    resp = client.get("/api/v1/hreis/leaves/")
    assert resp.status_code == status.HTTP_200_OK
    results = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
    assert len(results) == 0


def test_uc_016_employee_cannot_access_other_employee_request(auth_client_factory):
    """TEST-UC-016 [HR-UC-005 Exception E1]: Verify employee cannot access another employee's request detail without authorization."""
    EmployeeServiceRecord.objects.create(
        user_id=222,
        employee_id="EMP0222",
        department="ME",
        designation="Assistant Professor",
        category="faculty",
    )
    EmployeeServiceRecord.objects.create(
        user_id=223,
        employee_id="EMP0223",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
    )
    other_leave = LeaveRequest.objects.create(
        user_id=222,
        leave_type="casual",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 2),
        duration_days=2,
        justification="Confidential leave",
        status="pending",
        current_authority_role="hod",
    )
    client, _ = auth_client_factory(user_id=223, role="faculty")
    resp = client.get(f"/api/v1/hreis/leaves/{other_leave.id}/")
    assert resp.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)
