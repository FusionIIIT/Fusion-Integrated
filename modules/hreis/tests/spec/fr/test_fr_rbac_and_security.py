import pytest
from rest_framework.test import APIClient
from conftest import make_session
from modules.hreis.models import EmployeeServiceRecord, HrAuditLog
from modules.hreis.registry import ROLE_GRANTS

pytestmark = pytest.mark.django_db


def test_fr_001_rbac_actor_permissions(auth_client_factory):
    """TEST-FR-001 [HR-AFR-001]: Verify HR-EIS operates under Fusion RBAC for actor permissions."""
    client_faculty, _ = auth_client_factory(user_id=101, role="faculty")
    resp_faculty = client_faculty.get("/api/v1/hreis/service-records/me/")
    assert resp_faculty.status_code == 200

    client_admin, _ = auth_client_factory(user_id=201, role="hr_admin")
    resp_admin = client_admin.get("/api/v1/hreis/service-records/")
    assert resp_admin.status_code == 200


def test_fr_002_enforce_rbac_unauthenticated(stub_iam):
    """TEST-FR-002 [HR-AFR-094]: Verify HR-EIS enforces Fusion RBAC by denying unauthenticated requests."""
    stub_iam(None)
    client = APIClient()
    response = client.get("/api/v1/hreis/service-records/me/")
    assert response.status_code == 401


def test_fr_003_multi_role_support(stub_iam):
    """TEST-FR-003 [HR-AFR-095]: Verify HR-EIS supports users holding multiple roles simultaneously."""
    combined_permissions = list(ROLE_GRANTS["faculty"]) + list(ROLE_GRANTS["hod"])
    session = make_session(
        user_id=105,
        kind="faculty",
        active_role="hod",
        roles=("faculty", "hod"),
        permissions=tuple(combined_permissions),
        modules=("hr_eis",),
    )
    stub_iam(session)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token tok-105")

    resp_self = client.get("/api/v1/hreis/service-records/me/")
    assert resp_self.status_code == 200

    resp_leaves = client.get("/api/v1/hreis/leaves/")
    assert resp_leaves.status_code == 200


def test_fr_004_role_assignment_institutional_authority(auth_client_factory):
    """TEST-FR-004 [HR-AFR-096]: Verify HR-EIS respects institutional authority control over role assignment."""
    client, _ = auth_client_factory(user_id=110, role="faculty")
    resp = client.post("/api/v1/hreis/admin/assign-role/", {"role": "hr_admin"})
    assert resp.status_code in (403, 404, 405)


def test_fr_005_role_reassignment_institutional_authority(auth_client_factory):
    """TEST-FR-005 [HR-AFR-097]: Verify HR-EIS respects institutional authority control over role reassignment."""
    client, _ = auth_client_factory(user_id=110, role="faculty")
    resp = client.post("/api/v1/hreis/admin/reassign-role/", {"user_id": 110, "new_role": "director"})
    assert resp.status_code in (403, 404, 405)


def test_fr_006_restrict_sensitive_data_to_authorized_roles(auth_client_factory):
    """TEST-FR-006 [HR-AFR-098]: Verify HR-EIS restricts access to sensitive data to authorized roles only."""
    client_faculty, _ = auth_client_factory(user_id=111, role="faculty")
    resp_audit = client_faculty.get("/api/v1/hreis/audit-logs/")
    assert resp_audit.status_code == 403

    client_admin, _ = auth_client_factory(user_id=202, role="hr_admin")
    resp_admin_audit = client_admin.get("/api/v1/hreis/audit-logs/")
    assert resp_admin_audit.status_code == 200


def test_fr_007_restrict_employees_to_own_data(auth_client_factory):
    """TEST-FR-007 [HR-AFR-099]: Verify HR-EIS restricts Employees to accessing only their own employee data."""
    rec_b = EmployeeServiceRecord.objects.create(
        user_id=113,
        employee_id="EMP0113",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 10},
    )

    client_a, _ = auth_client_factory(user_id=112, role="faculty")
    resp = client_a.get(f"/api/v1/hreis/service-records/{rec_b.id}/")
    assert resp.status_code in (403, 404)


def test_fr_008_prevent_unauthorized_access(auth_client_factory):
    """TEST-FR-008 [HR-AFR-100]: Verify HR-EIS prevents unauthorized access to HR-EIS data."""
    client, _ = auth_client_factory(user_id=114, role="faculty")
    resp = client.get("/api/v1/hreis/workflows/settings/")
    assert resp.status_code == 403


def test_fr_009_prevent_unauthorized_modification(auth_client_factory):
    """TEST-FR-009 [HR-AFR-101]: Verify HR-EIS prevents unauthorized modification of HR-EIS data."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=115,
        employee_id="EMP0115",
        department="ECE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 12},
    )
    client, _ = auth_client_factory(user_id=115, role="faculty")
    resp = client.patch(f"/api/v1/hreis/service-records/{rec.id}/", {"designation": "Professor"})
    assert resp.status_code == 403


def test_fr_106_payroll_rule_scope_boundary(auth_client_factory):
    """TEST-FR-106 [HR-AFR-104]: Verify HR-EIS respects payroll boundary by not modifying payroll rules."""
    client, _ = auth_client_factory(user_id=205, role="hr_admin")
    resp = client.post("/api/v1/hreis/payroll/rules/", {"rule": "allowance_pct", "value": 50})
    assert resp.status_code in (403, 404, 405)


def test_fr_107_salary_structure_scope_boundary(auth_client_factory):
    """TEST-FR-107 [HR-AFR-105]: Verify HR-EIS respects salary-structure boundary by not modifying salary structures."""
    client, _ = auth_client_factory(user_id=205, role="hr_admin")
    resp = client.post("/api/v1/hreis/payroll/salary-structures/", {"pay_band": "PB-4", "base": 144200})
    assert resp.status_code in (403, 404, 405)
