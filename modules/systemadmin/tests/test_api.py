"""API Integration Tests for System Admin Module Endpoints."""
import pytest
from datetime import date, timedelta
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.systemadmin.models.user_mgmt import BasicUserProfile
from modules.systemadmin.models.role_mgmt import RoleDefinition, RoleAssignment
from modules.systemadmin.models.archival import ArchivedUser, ArchivedHistoricalData, PermanentPurgeRequest
from modules.systemadmin.models.config import SystemAdminConfig
from modules.systemadmin.services.user_service import UserService
from modules.systemadmin.services.archival_service import ArchivalService
from modules.systemadmin.services.config_service import ConfigService

pytestmark = pytest.mark.django_db

ALL_SUPER_ADMIN_PERMS = (
    "systemadmin.dashboard.view",
    "systemadmin.user.view",
    "systemadmin.user.create",
    "systemadmin.user.edit",
    "systemadmin.user.status",
    "systemadmin.user.bulk",
    "systemadmin.role.view",
    "systemadmin.role.assign",
    "systemadmin.role.reassign",
    "systemadmin.role.revoke",
    "systemadmin.role.extend",
    "systemadmin.archive.view",
    "systemadmin.archive.execute",
    "systemadmin.archive.restore",
    "systemadmin.purge.request",
    "systemadmin.audit.view",
    "systemadmin.audit.report",
    "systemadmin.config.manage",
)

IT_HEAD_PERMS = (
    "systemadmin.dashboard.view",
    "systemadmin.archive.view",
    "systemadmin.purge.authorize",
    "systemadmin.audit.view",
)


def _super_admin_client(stub_iam):
    stub_iam(make_session(
        user_id=1,
        kind="staff",
        modules=("systemadmin",),
        permissions=ALL_SUPER_ADMIN_PERMS,
    ))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token sa-valid-token")
    return client


def _it_head_client(stub_iam):
    stub_iam(make_session(
        user_id=2,
        kind="staff",
        modules=("systemadmin",),
        permissions=IT_HEAD_PERMS,
    ))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token it-valid-token")
    return client


def test_unauthenticated_request_denied():
    client = APIClient()
    res = client.get("/api/v1/systemadmin/dashboard/")
    assert res.status_code in (401, 403)


def test_unauthorized_module_denied(stub_iam):
    stub_iam(make_session(
        user_id=99,
        kind="student",
        modules=("student_gymkhana",),  # NO systemadmin module
        permissions=(),
    ))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token student-token")
    res = client.get("/api/v1/systemadmin/dashboard/")
    assert res.status_code == 403


def test_dashboard_overview_endpoint(stub_iam):
    client = _super_admin_client(stub_iam)
    res = client.get("/api/v1/systemadmin/dashboard/")
    assert res.status_code == 200
    data = res.json()
    assert "users" in data
    assert "roles" in data
    assert "archival" in data
    assert "security" in data


def test_user_lifecycle_endpoints(stub_iam):
    client = _super_admin_client(stub_iam)

    # 1. Create User
    create_payload = {
        "institute_id": "2024CS555",
        "user_type": "student",
        "full_name": "API Student",
        "institute_email": "api.student@iiitdmj.ac.in",
        "date_of_joining": "2024-08-01",
        "department": "Computer Science and Engineering",
        "programme": "B.Tech",
        "discipline": "CSE",
        "batch_year": 2024,
    }
    create_res = client.post("/api/v1/systemadmin/users/create/", create_payload, format="json")
    assert create_res.status_code == 201
    user_id = create_res.json()["id"]

    # 2. List Users
    list_res = client.get("/api/v1/systemadmin/users/?search=2024CS555")
    assert list_res.status_code == 200
    assert list_res.json()["count"] >= 1

    # 3. User Detail
    detail_res = client.get(f"/api/v1/systemadmin/users/{user_id}/")
    assert detail_res.status_code == 200
    assert detail_res.json()["institute_id"] == "2024CS555"

    # 4. Update Profile
    update_res = client.patch(
        f"/api/v1/systemadmin/users/{user_id}/",
        {"contact_number": "+91-9988776655"},
        format="json",
    )
    assert update_res.status_code == 200
    assert update_res.json()["contact_number"] == "+91-9988776655"

    # 5. Deactivate
    deact_res = client.post(
        f"/api/v1/systemadmin/users/{user_id}/status/",
        {"action": "deactivate", "reason": "Academic Suspension"},
        format="json",
    )
    assert deact_res.status_code == 200
    assert deact_res.json()["status"] == "deactivated"

    # 6. Reactivate
    react_res = client.post(
        f"/api/v1/systemadmin/users/{user_id}/status/",
        {"action": "reactivate", "reason": "Suspension lifted"},
        format="json",
    )
    assert react_res.status_code == 200
    assert react_res.json()["status"] == "active"


def test_bulk_user_endpoints(stub_iam):
    client = _super_admin_client(stub_iam)

    bulk_users = [
        {
            "institute_id": f"2024CSAPI{i:02d}",
            "user_type": "student",
            "full_name": f"API Bulk {i}",
            "institute_email": f"apibulk{i}@iiitdmj.ac.in",
            "date_of_joining": "2024-08-01",
            "department": "Computer Science and Engineering",
            "programme": "B.Tech",
            "batch_year": 2024,
        }
        for i in range(1, 4)
    ]
    create_res = client.post("/api/v1/systemadmin/users/bulk-create/", {"users": bulk_users}, format="json")
    assert create_res.status_code == 201
    assert create_res.json()["success_count"] == 3

    created_ids = [u.id for u in BasicUserProfile.objects.filter(institute_id__startswith="2024CSAPI")]
    status_res = client.post(
        "/api/v1/systemadmin/users/bulk-status/",
        {"user_ids": created_ids, "action": "deactivate", "reason": "Batch cohort deactivation"},
        format="json",
    )
    assert status_res.status_code == 200
    assert status_res.json()["success_count"] == 3


def test_role_lifecycle_endpoints(stub_iam):
    client = _super_admin_client(stub_iam)
    today = date.today()

    faculty = UserService.create_basic_user(
        institute_id="FAC_API_01",
        user_type="faculty",
        full_name="Dr. API Faculty 1",
        institute_email="facapi1@iiitdmj.ac.in",
        date_of_joining=today,
        department="Computer Science and Engineering",
        employee_id="EMP-API-01",
    )
    faculty2 = UserService.create_basic_user(
        institute_id="FAC_API_02",
        user_type="faculty",
        full_name="Dr. API Faculty 2",
        institute_email="facapi2@iiitdmj.ac.in",
        date_of_joining=today,
        department="Computer Science and Engineering",
        employee_id="EMP-API-02",
    )
    role = RoleDefinition.objects.create(
        code="API_ROLE_HOD",
        name="API Head of Dept",
        description="API Test Role",
        module_or_dept="Computer Science and Engineering",
        allowed_user_types=["faculty"],
        is_singular=True,
        is_time_bound=True,
        default_validity_days=365,
    )

    # 1. List Roles
    roles_res = client.get("/api/v1/systemadmin/roles/")
    assert roles_res.status_code == 200

    # 2. Role Detail
    detail_res = client.get(f"/api/v1/systemadmin/roles/{role.id}/")
    assert detail_res.status_code == 200

    # 3. Assign Role
    assign_payload = {
        "role_code": "API_ROLE_HOD",
        "user_id": faculty.id,
        "start_date": str(today),
        "end_date": str(today + timedelta(days=365)),
        "reason": "Appointed HOD",
    }
    assign_res = client.post("/api/v1/systemadmin/assignments/create/", assign_payload, format="json")
    assert assign_res.status_code == 201
    assignment_id = assign_res.json()["id"]

    # 4. Extend Role
    extend_res = client.post(
        f"/api/v1/systemadmin/assignments/{assignment_id}/extend/",
        {
            "new_end_date": str(today + timedelta(days=500)),
            "extension_approval_ref": "APP/EXT/001",
            "reason": "Extension approved by Director",
        },
        format="json",
    )
    assert extend_res.status_code == 200
    assert extend_res.json()["status"] == "extended"

    # 5. Reassign Role
    reassign_res = client.post(
        f"/api/v1/systemadmin/assignments/{assignment_id}/reassign/",
        {
            "new_user_id": faculty2.id,
            "effective_date": str(today + timedelta(days=2)),
            "reason": "Tenure completed handover",
            "pending_task_disposition": "transfer",
        },
        format="json",
    )
    assert reassign_res.status_code == 200
    new_assignment_id = reassign_res.json()["id"]

    # 6. Revoke New Role (Emergency)
    revoke_res = client.post(
        f"/api/v1/systemadmin/assignments/{new_assignment_id}/revoke/",
        {
            "reason": "Emergency role revocation",
            "is_emergency": True,
            "pending_task_disposition": "close",
        },
        format="json",
    )
    assert revoke_res.status_code == 200
    assert revoke_res.json()["status"] == "revoked"


def test_archival_and_dual_auth_purge_endpoints(stub_iam):
    sa_client = _super_admin_client(stub_iam)
    today = date.today()

    user = UserService.create_basic_user(
        institute_id="ARC_API_U1",
        user_type="student",
        full_name="Graduated API User",
        institute_email="gradapi@iiitdmj.ac.in",
        date_of_joining=today - timedelta(days=1500),
        department="Computer Science and Engineering",
        programme="B.Tech",
        batch_year=2020,
    )
    user = UserService.deactivate_user(user.id, reason="Graduated", actor_username="superadmin")
    # Backdate deactivation so interval has elapsed
    user.deactivated_at = timezone.now() - timedelta(days=35)
    user.save()

    # 1. Archive User
    arch_res = sa_client.post(
        "/api/v1/systemadmin/archival/users/create/",
        {"user_id": user.id, "reason": "Standard graduation archival"},
        format="json",
    )
    assert arch_res.status_code == 201

    # 2. Archive Historical Data
    hist_payload = {
        "category": "api_system_logs_2016",
        "date_range_start": "2016-01-01",
        "date_range_end": "2016-12-31",
        "record_count": 8000,
        "storage_size_kb": 25000,
        "backup_reference": "BK_API_2016",
        "retention_years": 7,
    }
    hist_res = sa_client.post("/api/v1/systemadmin/archival/historical/create/", hist_payload, format="json")
    assert hist_res.status_code == 201
    hist_id = hist_res.json()["id"]

    # 3. Super Admin requests permanent purge (Dual Auth Gate 1)
    purge_req_res = sa_client.post(
        "/api/v1/systemadmin/purge-requests/create/",
        {
            "target_type": "historical_data",
            "target_id": hist_id,
            "reason": "Statutory retention expired beyond 8 years",
            "regulatory_authorization_ref": "REG/PURGE/API/01",
        },
        format="json",
    )
    assert purge_req_res.status_code == 201
    purge_req_id = purge_req_res.json()["id"]

    # 4. Super Admin CANNOT authorize purge (Dual Auth Separation)
    sa_auth_attempt = sa_client.post(
        f"/api/v1/systemadmin/purge-requests/{purge_req_id}/authorize/",
        {"decision": "approve", "comments": "Self approval attempt"},
        format="json",
    )
    assert sa_auth_attempt.status_code == 403  # Forbidden

    # 5. Switch to IT Head and authorize purge (Dual Auth Gate 2)
    it_client = _it_head_client(stub_iam)
    it_auth_res = it_client.post(
        f"/api/v1/systemadmin/purge-requests/{purge_req_id}/authorize/",
        {"decision": "approve", "comments": "Permanent destruction authorized by IT Head"},
        format="json",
    )
    assert it_auth_res.status_code == 200
    assert it_auth_res.json()["status"] == "approved"


def test_configuration_endpoints(stub_iam):
    client = _super_admin_client(stub_iam)

    # 1. Get configurations
    list_res = client.get("/api/v1/systemadmin/config/")
    assert list_res.status_code == 200
    assert list_res.json()["count"] > 0

    # 2. Update permitted parameter
    update_res = client.patch(
        "/api/v1/systemadmin/config/password_min_length/",
        {"value": 10},
        format="json",
    )
    assert update_res.status_code == 200
    assert update_res.json()["value"] == 10

    # 3. Reject operational parameter
    reject_res = client.patch(
        "/api/v1/systemadmin/config/operational_grade_scale/",
        {"value": "10-point"},
        format="json",
    )
    assert reject_res.status_code == 400


def test_audit_and_notification_endpoints(stub_iam):
    client = _super_admin_client(stub_iam)

    # 1. Audit logs
    audit_res = client.get("/api/v1/systemadmin/audit/")
    assert audit_res.status_code == 200
    assert "results" in audit_res.json()

    # 2. Audit reports
    report_res = client.get("/api/v1/systemadmin/audit/reports/")
    assert report_res.status_code == 200
    assert "total_actions" in report_res.json()

    # 3. Notifications
    notif_res = client.get("/api/v1/systemadmin/notifications/")
    assert notif_res.status_code == 200
