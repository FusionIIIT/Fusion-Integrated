"""End-to-end backend journey tests for System Admin module."""
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.system_admin.models import (
    ArchivedUserRecord,
    PermanentPurgeRequest,
    RoleAssignment,
    SystemAuditLog,
    SystemParameter,
    UserAccount,
)

pytestmark = pytest.mark.django_db

FULL_ADMIN_PERMS = (
    "system_admin.user.view",
    "system_admin.user.add",
    "system_admin.user.change",
    "system_admin.role.view",
    "system_admin.role.manage",
    "system_admin.archive.view",
    "system_admin.archive.manage",
    "system_admin.audit.view",
    "system_admin.config.view",
    "system_admin.config.change",
)


def _admin_client(stub_iam, uid=100):
    stub_iam(
        make_session(
            user_id=uid,
            kind="staff",
            modules=("system_admin",),
            permissions=FULL_ADMIN_PERMS,
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Token admin-token-{uid}")
    return c


def test_complete_user_lifecycle_journey(stub_iam):
    """Journey test: Provision user -> Assign role -> Revoke role -> Deactivate -> Archive -> Purge."""
    client = _admin_client(stub_iam, uid=100)

    # 1. Provision user
    res = client.post(
        "/api/v1/system_admin/users/create/",
        {
            "user_id": 5001,
            "institute_id": "FAC5001",
            "username": "journey_user",
            "email": "journey@iiitdmj.ac.in",
            "user_type": "faculty",
            "department": "CSE",
        },
    )
    assert res.status_code == 201
    assert UserAccount.objects.filter(user_id=5001, status="active").exists()

    # 2. Assign role
    res = client.post(
        "/api/v1/system_admin/roles/assign/",
        {
            "user_id": 5001,
            "role_code": "faculty",
            "start_date": "2026-01-01",
        },
    )
    assert res.status_code == 201
    assignment_id = res.data["id"]
    assert RoleAssignment.objects.filter(id=assignment_id, status="active").exists()

    # 3. Revoke role
    res = client.post(
        f"/api/v1/system_admin/roles/{assignment_id}/revoke/",
        {"reason": "Role tenure ended"},
    )
    assert res.status_code == 200
    assert RoleAssignment.objects.filter(id=assignment_id, status="revoked").exists()

    # 4. Deactivate user
    res = client.post(
        "/api/v1/system_admin/users/5001/status/",
        {"action": "deactivate", "reason": "Faculty member resigned"},
    )
    assert res.status_code == 200
    assert UserAccount.objects.filter(user_id=5001, status="deactivated").exists()

    # 5. Archive user
    res = client.post(
        "/api/v1/system_admin/archives/user/",
        {"user_id": 5001, "reason": "Retention archiving"},
    )
    assert res.status_code == 201
    archived_rec = ArchivedUserRecord.objects.get(user_id=5001)
    assert archived_rec.user_id == 5001
    assert UserAccount.objects.get(user_id=5001).status == "archived"

    # 6. Initiate purge
    res = client.post(
        "/api/v1/system_admin/archives/purge-request/",
        {"dataset_identifier": f"user-{archived_rec.user_id}", "retention_years": 7, "reason": "GDPR compliance removal"},
    )
    assert res.status_code == 201
    purge_req_id = res.data["id"]
    assert PermanentPurgeRequest.objects.filter(id=purge_req_id, status="pending_it_head").exists()

    # 7. Dual authorization approve purge with second admin
    head_client = _admin_client(stub_iam, uid=200)
    res = head_client.post(
        f"/api/v1/system_admin/archives/purge-request/{purge_req_id}/authorize/",
        {"approve": True, "remarks": "Authorized by IT Head"},
    )
    assert res.status_code == 200
    assert PermanentPurgeRequest.objects.filter(id=purge_req_id, status="purged").exists()

    # Verify audit logs captured events
    logs = SystemAuditLog.objects.filter(target_id__in=["5001", str(archived_rec.user_id), str(purge_req_id)])
    assert logs.count() >= 3


def test_bulk_user_provisioning_and_config_journey(stub_iam):
    """Journey test: Bulk import -> Config update."""
    client = _admin_client(stub_iam, uid=100)

    # 1. Bulk import
    rows = [
        {
            "user_id": 6001,
            "institute_id": "STU6001",
            "username": "bulk_1",
            "email": "b1@iiitdmj.ac.in",
            "user_type": "student",
            "programme": "B.Tech",
            "discipline": "CSE",
            "batch_year": 2024,
        },
        {
            "user_id": 6002,
            "institute_id": "STU6002",
            "username": "bulk_2",
            "email": "b2@iiitdmj.ac.in",
            "user_type": "student",
            "programme": "B.Tech",
            "discipline": "ECE",
            "batch_year": 2024,
        },
    ]
    res = client.post("/api/v1/system_admin/users/bulk-create/", {"users": rows}, format="json")
    assert res.status_code == 201
    assert res.data["created_count"] == 2
    assert UserAccount.objects.filter(user_id__in=[6001, 6002]).count() == 2

    # 2. Config update
    res = client.patch(
        "/api/v1/system_admin/config/",
        {"parameters": {"session_timeout_minutes": "45"}},
        format="json",
    )
    assert res.status_code == 200
    config_entry = SystemParameter.objects.get(key="session_timeout_minutes")
    assert config_entry.value == "45"
