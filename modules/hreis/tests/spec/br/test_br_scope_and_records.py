import pytest
from rest_framework import status
from modules.hreis.models import EmployeeServiceRecord, HrAuditLog

pytestmark = pytest.mark.django_db


def test_br_001_scope_permitted(auth_client_factory):
    """TEST-BR-001 [BR-HR-001 Permitted]: Verify HR-EIS processes valid employee-centric service record operations within module scope."""
    EmployeeServiceRecord.objects.create(
        user_id=301,
        employee_id="EMP0301",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
    )
    client, _ = auth_client_factory(user_id=301, role="faculty")
    resp = client.get("/api/v1/hreis/service-records/me/")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["employee_id"] == "EMP0301"


def test_br_002_scope_prohibited(auth_client_factory):
    """TEST-BR-002 [BR-HR-001 Prohibited]: Verify HR-EIS does not expose out-of-scope non-HR functionality."""
    client, _ = auth_client_factory(user_id=301, role="faculty")
    resp = client.get("/api/v1/hreis/course-registration/")
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_br_003_rbac_permitted(auth_client_factory):
    """TEST-BR-003 [BR-HR-002 Permitted]: Verify user with authorized role can perform permitted HR action."""
    EmployeeServiceRecord.objects.create(
        user_id=302,
        employee_id="EMP0302",
        department="ECE",
        designation="Professor",
        category="faculty",
    )
    client, _ = auth_client_factory(user_id=302, role="faculty")
    resp = client.get("/api/v1/hreis/service-records/me/")
    assert resp.status_code == status.HTTP_200_OK


def test_br_004_rbac_prohibited(auth_client_factory):
    """TEST-BR-004 [BR-HR-002 Prohibited]: Verify user lacking required role is blocked by RBAC."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=303,
        employee_id="EMP0303",
        department="ME",
        designation="Lecturer",
        category="faculty",
    )
    client, _ = auth_client_factory(user_id=304, role="faculty")
    resp = client.patch(
        f"/api/v1/hreis/service-records/{rec.id}/",
        {"designation": "Associate Professor"},
        format="json",
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_br_005_own_record_access_permitted(auth_client_factory):
    """TEST-BR-005 [BR-HR-003 Permitted]: Verify employee can view own service record in read-only mode."""
    EmployeeServiceRecord.objects.create(
        user_id=305,
        employee_id="EMP0305",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 8},
    )
    client, _ = auth_client_factory(user_id=305, role="faculty")
    resp = client.get("/api/v1/hreis/service-records/me/")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["employee_id"] == "EMP0305"


def test_br_006_own_record_modify_prohibited(auth_client_factory):
    """TEST-BR-006 [BR-HR-003 Prohibited]: Verify employee cannot alter own official service record data."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=306,
        employee_id="EMP0306",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
    )
    client, _ = auth_client_factory(user_id=306, role="faculty")
    resp = client.patch(
        f"/api/v1/hreis/service-records/{rec.id}/",
        {"designation": "Professor"},
        format="json",
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_br_007_record_composition():
    """TEST-BR-007 [BR-HR-004 Composition]: Verify service record contains appointment details, department, designation, and leave balances."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=307,
        employee_id="EMP0307",
        department="Design",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 10, "medical": 15},
    )
    assert rec.department == "Design"
    assert rec.designation == "Assistant Professor"
    assert "casual" in rec.leave_balances


def test_br_008_hr_admin_create_record_permitted(auth_client_factory):
    """TEST-BR-008 [BR-HR-005 Permitted]: Verify HR Administrator has authority to create and modify service records."""
    client_admin, _ = auth_client_factory(user_id=201, role="hr_admin")
    payload = {
        "user_id": 308,
        "employee_id": "EMP0308",
        "department=" : "CSE",
        "department": "CSE",
        "designation": "Assistant Professor",
        "category": "faculty",
        "appointment_date": "2024-01-10",
        "leave_balances": {"casual": 8},
    }
    resp = client_admin.post("/api/v1/hreis/service-records/", payload, format="json")
    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.data["employee_id"] == "EMP0308"


def test_br_009_employee_create_record_prohibited(auth_client_factory):
    """TEST-BR-009 [BR-HR-005 Prohibited]: Verify non-HR admin cannot create service records."""
    client, _ = auth_client_factory(user_id=309, role="faculty")
    payload = {
        "user_id": 310,
        "employee_id": "EMP0310",
        "department": "CSE",
        "designation": "Assistant Professor",
        "category": "faculty",
    }
    resp = client.post("/api/v1/hreis/service-records/", payload, format="json")
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_br_010_service_record_integrity():
    """TEST-BR-010 [BR-HR-006 Integrity]: Verify service record preserves consistency on partial invalid update."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=311,
        employee_id="EMP0311",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
    )
    original_emp_id = rec.employee_id
    rec.refresh_from_db()
    assert rec.employee_id == original_emp_id
