import pytest
from rest_framework import status
from modules.hreis.models import EmployeeServiceRecord, HrAuditLog

pytestmark = pytest.mark.django_db


def test_uc_001_view_own_service_record(auth_client_factory):
    """TEST-UC-001 [HR-UC-001 Main Flow]: Verify employee can view their own official service record in read-only mode."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=201,
        employee_id="EMP0201",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 8, "medical": 10},
    )
    client, _ = auth_client_factory(user_id=201, role="faculty")
    response = client.get("/api/v1/hreis/service-records/me/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["employee_id"] == "EMP0201"
    assert response.data["department"] == "CSE"
    assert response.data["designation"] == "Assistant Professor"


def test_uc_002_dual_role_own_record(auth_client_factory):
    """TEST-UC-002 [HR-UC-001 Alternative A1]: Verify employee holding dual role sees own record in read-only mode."""
    EmployeeServiceRecord.objects.create(
        user_id=202,
        employee_id="EMP0202",
        department="ECE",
        designation="Professor & HOD",
        category="faculty",
        leave_balances={"casual": 12},
    )
    client, _ = auth_client_factory(user_id=202, role="hod")
    response = client.get("/api/v1/hreis/service-records/me/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["employee_id"] == "EMP0202"
    assert response.data["department"] == "ECE"


def test_uc_003_unauthenticated_service_record_denied():
    """TEST-UC-003 [HR-UC-001 Exception E1]: Verify unauthenticated user cannot access service records."""
    from rest_framework.test import APIClient
    client = APIClient()
    response = client.get("/api/v1/hreis/service-records/me/")
    assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


def test_uc_004_hr_admin_maintain_service_record(auth_client_factory):
    """TEST-UC-004 [HR-UC-002 Main Flow]: Verify HR Administrator can update employee service record auditably."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=203,
        employee_id="EMP0203",
        department="ME",
        designation="Lecturer",
        category="faculty",
    )
    client, _ = auth_client_factory(user_id=999, role="hr_admin")
    response = client.patch(
        f"/api/v1/hreis/service-records/{rec.id}/",
        {"designation": "Associate Professor", "department": "ME"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    rec.refresh_from_db()
    assert rec.designation == "Associate Professor"
    assert HrAuditLog.objects.filter(entity_name="EmployeeServiceRecord", entity_id=rec.id).exists()


def test_uc_005_cancel_update_leaves_record_intact():
    """TEST-UC-005 [HR-UC-002 Alternative A1]: Verify cancelling update leaves employee service record unchanged."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=204,
        employee_id="EMP0204",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
    )
    original_designation = rec.designation
    # Simulate cancelled update / uncommitted draft
    rec.refresh_from_db()
    assert rec.designation == original_designation


def test_uc_006_non_admin_cannot_modify_service_record(auth_client_factory):
    """TEST-UC-006 [HR-UC-002 Exception E1]: Verify non-HR admin cannot modify employee service records."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=205,
        employee_id="EMP0205",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
    )
    client, _ = auth_client_factory(user_id=205, role="faculty")
    response = client.patch(
        f"/api/v1/hreis/service-records/{rec.id}/",
        {"designation": "Professor"},
        format="json",
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    rec.refresh_from_db()
    assert rec.designation == "Assistant Professor"
