"""API endpoint tests with IAM authentication and permission gating."""
from datetime import date, timedelta

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.system_admin.models.user_account import UserAccount

pytestmark = pytest.mark.django_db


def _authed_client(stub_iam, permissions=(), user_id=1, kind="faculty"):
    session = make_session(
        user_id=user_id,
        kind=kind,
        modules=("system_admin",),
        permissions=permissions,
    )
    stub_iam(session)
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token mock-token")
    return c


def test_permission_denied_when_missing_permissions(stub_iam):
    client = _authed_client(stub_iam, permissions=())
    res = client.get("/api/v1/system_admin/users/")
    assert res.status_code == 403


def test_dashboard_endpoint(stub_iam):
    client = _authed_client(stub_iam, permissions=("system_admin.user.view",))
    res = client.get("/api/v1/system_admin/dashboard/")
    assert res.status_code == 200
    data = res.json()
    assert "users" in data
    assert "roles" in data
    assert "security" in data
    assert data["system_health"]["status"] == "healthy"


def test_user_lifecycle_endpoints(stub_iam):
    client = _authed_client(
        stub_iam,
        permissions=(
            "system_admin.user.view",
            "system_admin.user.add",
            "system_admin.user.change",
        ),
    )
    # 1. Create user
    payload = {
        "institute_id": "2024BCS301",
        "username": "api_user",
        "email": "api.user@iiitdmj.ac.in",
        "user_type": "student",
        "name": "API User",
        "programme": "B.Tech",
        "discipline": "CSE",
        "batch_year": 2024,
    }
    create_res = client.post("/api/v1/system_admin/users/create/", payload, format="json")
    assert create_res.status_code == 201
    user_id = create_res.json()["user_id"]

    # 2. Get user list with filters
    list_res = client.get("/api/v1/system_admin/users/?q=api_user&user_type=student&status=active")
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1

    # 3. Get user detail
    detail_res = client.get(f"/api/v1/system_admin/users/{user_id}/")
    assert detail_res.status_code == 200
    assert detail_res.json()["username"] == "api_user"

    # 4. Update profile
    patch_res = client.patch(
        f"/api/v1/system_admin/users/{user_id}/",
        {"name": "API User Updated"},
        format="json",
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["name"] == "API User Updated"

    # 5. Deactivate status
    deact_res = client.post(
        f"/api/v1/system_admin/users/{user_id}/status/",
        {"action": "deactivate", "reason": "Testing deactivation"},
        format="json",
    )
    assert deact_res.status_code == 200
    assert deact_res.json()["status"] == "deactivated"

    # 6. Reactivate status
    react_res = client.post(
        f"/api/v1/system_admin/users/{user_id}/status/",
        {"action": "reactivate", "reason": "Testing reactivation"},
        format="json",
    )
    assert react_res.status_code == 200
    assert react_res.json()["status"] == "active"

    # 7. Bulk create users
    bulk_payload = {
        "users": [
            {
                "institute_id": "2024BCS302",
                "username": "bulk_1",
                "email": "bulk1@iiitdmj.ac.in",
                "user_type": "student",
                "programme": "B.Tech",
                "discipline": "CSE",
                "batch_year": 2024,
            }
        ]
    }
    bulk_res = client.post("/api/v1/system_admin/users/bulk-create/", bulk_payload, format="json")
    assert bulk_res.status_code == 201
    assert bulk_res.json()["created_count"] == 1


def test_role_endpoints(stub_iam):
    client = _authed_client(
        stub_iam,
        permissions=(
            "system_admin.user.add",
            "system_admin.role.view",
            "system_admin.role.manage",
        ),
    )
    # Create faculty users
    u1 = UserAccount.objects.create(
        user_id=9001,
        institute_id="FAC901",
        username="fac_role_test1",
        email="fac.role1@iiitdmj.ac.in",
        user_type="faculty",
        department="CSE",
        status="active",
    )
    u2 = UserAccount.objects.create(
        user_id=9002,
        institute_id="FAC902",
        username="fac_role_test2",
        email="fac.role2@iiitdmj.ac.in",
        user_type="faculty",
        department="CSE",
        status="active",
    )

    # 1. View Directory
    dir_res = client.get("/api/v1/system_admin/roles/?mode=directory")
    assert dir_res.status_code == 200
    assert len(dir_res.json()) > 0

    # 2. Assign Role
    today = date.today()
    assign_payload = {
        "role_code": "dean_rnd",
        "user_id": u1.user_id,
        "start_date": str(today),
        "end_date": str(today + timedelta(days=365)),
        "is_singular": True,
        "reason": "Test assign",
    }
    assign_res = client.post("/api/v1/system_admin/roles/assign/", assign_payload, format="json")
    assert assign_res.status_code == 201
    role_id = assign_res.json()["id"]

    # 3. List Roles
    list_res = client.get(f"/api/v1/system_admin/roles/?user_id={u1.user_id}")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    # 4. Reassign Role
    reassign_payload = {
        "new_user_id": u2.user_id,
        "effective_date": str(today),
        "reason": "Reassigning Dean RnD",
    }
    reassign_res = client.post(
        f"/api/v1/system_admin/roles/{role_id}/reassign/", reassign_payload, format="json"
    )
    assert reassign_res.status_code == 200
    new_role_id = reassign_res.json()["id"]

    # 5. Extend Role
    extend_payload = {
        "new_end_date": str(today + timedelta(days=500)),
        "reason": "Extension",
    }
    extend_res = client.post(
        f"/api/v1/system_admin/roles/{new_role_id}/extend/", extend_payload, format="json"
    )
    assert extend_res.status_code == 200

    # 6. Revoke Role
    revoke_res = client.post(
        f"/api/v1/system_admin/roles/{new_role_id}/revoke/",
        {"reason": "Testing revocation"},
        format="json",
    )
    assert revoke_res.status_code == 200
    assert revoke_res.json()["status"] == "revoked"


def test_archive_and_purge_endpoints(stub_iam):
    client = _authed_client(
        stub_iam,
        permissions=(
            "system_admin.archive.view",
            "system_admin.archive.manage",
        ),
        user_id=1,
    )
    # Create deactivated user
    u = UserAccount.objects.create(
        user_id=9003,
        institute_id="2024BCS903",
        username="arch_test",
        email="arch.test@iiitdmj.ac.in",
        user_type="student",
        status="deactivated",
    )

    # 1. Archive user
    arch_res = client.post(
        "/api/v1/system_admin/archives/user/",
        {"user_id": u.user_id, "reason": "Archiving test"},
        format="json",
    )
    assert arch_res.status_code == 201

    # 2. List archives
    list_res = client.get("/api/v1/system_admin/archives/")
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1

    # 3. Archive historical dataset
    today = date.today()
    ds_res = client.post(
        "/api/v1/system_admin/archives/dataset/",
        {
            "category": "academic_records",
            "description": "2015-2019 Graduated Batches",
            "date_range_start": str(today - timedelta(days=2000)),
            "date_range_end": str(today - timedelta(days=1000)),
            "record_count": 450,
            "backup_reference": "s3://backups/academic_2015_2019.tar.gz",
        },
        format="json",
    )
    assert ds_res.status_code == 201

    # 4. List datasets mode
    ds_list_res = client.get("/api/v1/system_admin/archives/?mode=datasets")
    assert ds_list_res.status_code == 200
    assert len(ds_list_res.json()) >= 1

    # 5. Restore user
    restore_res = client.post(
        f"/api/v1/system_admin/archives/user/{u.user_id}/restore/",
        {"reason": "Restoring test"},
        format="json",
    )
    assert restore_res.status_code == 200
    assert restore_res.json()["status"] == "active"

    # 6. Request permanent purge
    purge_req_res = client.post(
        "/api/v1/system_admin/archives/purge-request/",
        {
            "dataset_identifier": "test_dataset_old",
            "retention_years": 8.5,
            "reason": "Retention elapsed",
        },
        format="json",
    )
    assert purge_req_res.status_code == 201
    purge_id = purge_req_res.json()["id"]

    # 7. List purge requests mode
    purge_list_res = client.get("/api/v1/system_admin/archives/?mode=purge_requests")
    assert purge_list_res.status_code == 200
    assert len(purge_list_res.json()) >= 1

    # 8. Dual authorization - IT Head (user_id=99)
    it_client = _authed_client(
        stub_iam,
        permissions=("system_admin.archive.manage",),
        user_id=99,
        kind="staff",
    )
    auth_res = it_client.post(
        f"/api/v1/system_admin/archives/purge-request/{purge_id}/authorize/",
        {"approve": True, "remarks": "Authorized by IT Head"},
        format="json",
    )
    assert auth_res.status_code == 200
    assert auth_res.json()["status"] == "purged"


def test_audit_endpoints(stub_iam):
    client = _authed_client(
        stub_iam,
        permissions=("system_admin.audit.view",),
    )
    # 1. Audit logs
    audit_res = client.get("/api/v1/system_admin/audit/?limit=20")
    assert audit_res.status_code == 200
    assert "results" in audit_res.json()

    # 2. Failed logins
    failed_res = client.get("/api/v1/system_admin/audit/failed-logins/")
    assert failed_res.status_code == 200


def test_config_endpoint(stub_iam):
    client = _authed_client(
        stub_iam,
        permissions=("system_admin.config.change",),
    )
    # Get config
    get_res = client.get("/api/v1/system_admin/config/")
    assert get_res.status_code == 200

    # Patch config
    patch_res = client.patch(
        "/api/v1/system_admin/config/",
        {"parameters": {"bulk_operation_limit": "500", "session_timeout_minutes": "45"}},
        format="json",
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["parameters"]["bulk_operation_limit"] == "500"


def test_additional_api_error_branches(stub_iam):
    client = _authed_client(
        stub_iam,
        permissions=(
            "system_admin.user.view",
            "system_admin.user.add",
            "system_admin.user.change",
            "system_admin.role.view",
            "system_admin.role.manage",
            "system_admin.archive.view",
            "system_admin.archive.manage",
        ),
    )
    # UserDetail 404
    res = client.get("/api/v1/system_admin/users/999999/")
    assert res.status_code == 404

    # UserUpdate 404
    res = client.patch(
        "/api/v1/system_admin/users/999999/",
        {"contact_number": "1234567890"},
        format="json",
    )
    assert res.status_code == 404

    # UserStatus 404
    res = client.post(
        "/api/v1/system_admin/users/999999/status/",
        {"action": "deactivate"},
        format="json",
    )
    assert res.status_code == 404

    # RoleAssign 404 or 400
    res = client.post(
        "/api/v1/system_admin/roles/assign/",
        {"role_code": "tutor", "user_id": 999999, "start_date": "2026-01-01"},
        format="json",
    )
    assert res.status_code in (400, 404)

    # UserUpdate 400
    u_obj = UserAccount.objects.create(
        user_id=8888,
        institute_id="UPD_TEST",
        username="upd_test",
        email="upd@iiitdmj.ac.in",
        user_type="student",
        batch_year=2024,
    )
    res = client.patch(
        f"/api/v1/system_admin/users/{u_obj.user_id}/",
        {"email": "not_an_email_domain@invalid.com"},
        format="json",
    )
    assert res.status_code == 400

    # Purge request with insufficient retention
    res = client.post(
        "/api/v1/system_admin/archives/purge-request/",
        {
            "dataset_identifier": "ds_recent",
            "retention_years": 2,
            "reason": "premature purge",
        },
        format="json",
    )
    assert res.status_code == 400

    # Purge authorize dual auth violation
    from modules.system_admin.models.archive import PermanentPurgeRequest
    p_req = PermanentPurgeRequest.objects.create(
        dataset_identifier="ds_old",
        requested_by=1,
        retention_verified=True,
        reason="old data",
        status="pending_it_head",
    )
    res = client.post(
        f"/api/v1/system_admin/archives/purge-request/{p_req.id}/authorize/",
        {"approve": True, "remarks": "same user"},
        format="json",
    )
    assert res.status_code == 409

    # RoleExtend invalid date
    from modules.system_admin.models.role_assignment import RoleAssignment
    ra = RoleAssignment.objects.create(
        role_code="tutor",
        user_id=u_obj.user_id,
        status="active",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 6, 30),
        assigned_by=1,
    )
    res = client.post(
        f"/api/v1/system_admin/roles/{ra.id}/extend/",
        {"new_end_date": "2025-01-01", "reason": "past date"},
        format="json",
    )
    assert res.status_code == 400

    # RoleReassign invalid
    res = client.post(
        f"/api/v1/system_admin/roles/{ra.id}/reassign/",
        {"new_user_id": 999999, "effective_date": "2026-02-01", "reason": "non existent"},
        format="json",
    )
    assert res.status_code in (400, 404)

    # Bulk create users
    res = client.post(
        "/api/v1/system_admin/users/bulk-create/",
        {
            "users": [
                {
                    "institute_id": "BULK_1",
                    "username": "bulk_1",
                    "email": "b1@iiitdmj.ac.in",
                    "user_type": "student",
                },
                {
                    "institute_id": "BULK_2",
                    "username": "bulk_2",
                    "email": "b2@iiitdmj.ac.in",
                    "user_type": "faculty",
                },
            ]
        },
        format="json",
    )
    assert res.status_code == 201

    # Status deactivate
    res = client.post(
        f"/api/v1/system_admin/users/{u_obj.user_id}/status/",
        {"action": "deactivate", "reason": "testing deactivate"},
        format="json",
    )
    assert res.status_code == 200

    # User roles property & QuerySet get
    assert u_obj.roles.count() >= 1
    ra_fetched = RoleAssignment.objects.get(user=u_obj, id=ra.id)
    assert ra_fetched.id == ra.id

    # RoleRevoke already revoked
    client.post(
        f"/api/v1/system_admin/roles/{ra.id}/revoke/",
        {"reason": "first revoke"},
        format="json",
    )
    res = client.post(
        f"/api/v1/system_admin/roles/{ra.id}/revoke/",
        {"reason": "second revoke"},
        format="json",
    )
    assert res.status_code == 400

    # RoleReassign 404
    res = client.post(
        "/api/v1/system_admin/roles/999999/reassign/",
        {"new_user_id": 1, "effective_date": "2026-01-01", "reason": "test"},
        format="json",
    )
    assert res.status_code == 404

    # RoleRevoke 404
    res = client.post(
        "/api/v1/system_admin/roles/999999/revoke/",
        {"reason": "test"},
        format="json",
    )
    assert res.status_code == 404

    # RoleExtend 404
    res = client.post(
        "/api/v1/system_admin/roles/999999/extend/",
        {"new_end_date": "2026-12-31", "reason": "test"},
        format="json",
    )
    assert res.status_code == 404

    # Archive user 404
    res = client.post(
        "/api/v1/system_admin/archives/user/",
        {"user_id": 999999, "reason": "test"},
        format="json",
    )
    assert res.status_code == 404

    # Archive restore 404 or 400
    res = client.post(
        "/api/v1/system_admin/archives/user/999999/restore/",
        {"reason": "test"},
        format="json",
    )
    assert res.status_code in (400, 404)

    # Models string and properties
    from modules.system_admin.models.audit import (
        AdminSessionLog,
        FailedLoginLog,
        SystemAuditLog,
    )
    from modules.system_admin.models.role_assignment import RoleAssignment

    r = RoleAssignment(
        role_code="tutor",
        user_id=1,
        status="active",
        start_date="2026-01-01",
        assigned_by=1,
    )
    assert "tutor" in str(r)
    log = SystemAuditLog.objects.create(
        actor_id=1,
        action="test",
        target="tgt",
        details={"a": 1},
    )
    assert log.target == "tgt"
    assert log.details == {"a": 1}
    assert "test" in str(log)
    s = AdminSessionLog(user_id=1, session_key="sk1")
    assert "sk1" in str(s) or "1" in str(s)
    fl = FailedLoginLog(username="usr")
    assert "usr" in str(fl)

