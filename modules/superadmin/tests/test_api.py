"""Integration tests for Super Admin API endpoints."""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.superadmin.models import (
    HistoricalArchiveRecord,
    UserAccountRecord,
)

pytestmark = pytest.mark.django_db

ALL_SUPERADMIN_PERMS = (
    "superadmin.user.view",
    "superadmin.user.create",
    "superadmin.user.update",
    "superadmin.user.delete",
    "superadmin.user.restore",
    "superadmin.user.import",
    "superadmin.user.export",
    "superadmin.role.view",
    "superadmin.role.assign",
    "superadmin.role.revoke",
    "superadmin.role.update",
    "superadmin.archive.view",
    "superadmin.archive.create",
    "superadmin.archive.restore",
    "superadmin.archive.export",
    "superadmin.purge.create",
    "superadmin.audit_log.view",
    "superadmin.audit_log.export",
    "superadmin.system_config.view",
    "superadmin.system_config.update",
)


def _client(stub_iam, uid=1001, perms=ALL_SUPERADMIN_PERMS):
    stub_iam(
        make_session(
            user_id=uid,
            kind="staff",
            permissions=perms,
            modules=("superadmin",),
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token tok-123", HTTP_X_STEP_UP_AUTH="verified")
    return c


def test_create_and_get_user(stub_iam):
    client = _client(stub_iam)

    payload = {
        "user_id": 5001,
        "institute_id": "24BCS501",
        "email": "user5001@iiitdmj.ac.in",
        "user_type": "STUDENT",
        "program": "B.Tech",
        "batch": "2024",
    }
    res = client.post("/api/v1/superadmin/users/", payload, format="json")
    assert res.status_code == 201
    assert res.data["user_id"] == 5001
    assert res.data["activation_status"] == "ACTIVE"

    # Detail
    res_get = client.get("/api/v1/superadmin/users/5001/")
    assert res_get.status_code == 200
    assert res_get.data["institute_id"] == "24BCS501"


def test_user_lifecycle_deactivate_reactivate(stub_iam):
    client = _client(stub_iam)
    UserAccountRecord.objects.create(
        user_id=5002,
        institute_id="24BCS502",
        email="u5002@iiitdmj.ac.in",
        user_type="STUDENT",
        activation_status="ACTIVE",
    )

    # Deactivate
    res_deact = client.post(
        "/api/v1/superadmin/users/5002/deactivate/", {"reason": "Leave of absence"}, format="json"
    )
    assert res_deact.status_code == 200
    assert res_deact.data["activation_status"] == "DEACTIVATED"

    # Reactivate
    res_react = client.post(
        "/api/v1/superadmin/users/5002/reactivate/",
        {"reason": "Returned from leave"},
        format="json",
    )
    assert res_react.status_code == 200
    assert res_react.data["activation_status"] == "ACTIVE"


def test_user_archive_and_restore_within_window(stub_iam):
    client = _client(stub_iam)
    UserAccountRecord.objects.create(
        user_id=5003,
        institute_id="24BCS503",
        email="u5003@iiitdmj.ac.in",
        user_type="STUDENT",
        activation_status="DEACTIVATED",
        deactivation_date=timezone.now() - timedelta(days=35),
    )

    # Archive
    res_arch = client.post(
        "/api/v1/superadmin/users/5003/archive/", {"reason": "Graduated student"}, format="json"
    )
    assert res_arch.status_code == 200
    assert res_arch.data["activation_status"] == "ARCHIVED_REVERSIBLE"
    assert res_arch.data["reversibility_expires_at"] is not None

    # Restore within window
    res_rest = client.post(
        "/api/v1/superadmin/users/5003/restore/",
        {"reason": "Post-graduate re-enrollment"},
        format="json",
    )
    assert res_rest.status_code == 200
    assert res_rest.data["activation_status"] == "ACTIVE"


def test_role_assignment_and_revocation(stub_iam):
    client = _client(stub_iam)
    UserAccountRecord.objects.create(
        user_id=6001,
        institute_id="FAC_CSE_601",
        email="fac601@iiitdmj.ac.in",
        user_type="FACULTY",
        activation_status="ACTIVE",
    )

    now = timezone.now()
    role_payload = {
        "user_id": 6001,
        "role_name": "Course Instructor",
        "valid_from": now.isoformat(),
        "valid_to": (now + timedelta(days=120)).isoformat(),
        "reason": "Spring semester duty",
    }
    res_assign = client.post("/api/v1/superadmin/roles/", role_payload, format="json")
    assert res_assign.status_code == 201
    assignment_id = res_assign.data["id"]

    # Revoke
    res_revoke = client.post(
        f"/api/v1/superadmin/roles/{assignment_id}/revoke/",
        {"reason": "Semester concluded"},
        format="json",
    )
    assert res_revoke.status_code == 200
    assert res_revoke.data["status"] == "REVOKED"


def test_purge_request_and_dual_authorization(stub_iam):
    super_admin_client = _client(stub_iam, uid=1001)

    # Create an archive record eligible for purge
    archive = HistoricalArchiveRecord.objects.create(
        entity_type="OLD_GRADES",
        record_identifier="GRADES_2015",
        payload={"count": 100},
        retention_period_days=365,
        purge_eligible_at=timezone.now() - timedelta(days=10),
        status="ACTIVE_ARCHIVE",
        archived_by_user_id=1001,
    )

    # Request purge
    res_req = super_admin_client.post(
        "/api/v1/superadmin/purge/requests/",
        {"archive_id": archive.id, "reason": "Retention expired"},
        format="json",
    )
    assert res_req.status_code == 201
    purge_id = res_req.data["id"]
    assert res_req.data["status"] == "REQUESTED"

    # Authorize with IT Head (different user, uid=2002)
    it_head_client = _client(stub_iam, uid=2002, perms=("superadmin.purge.approve",))
    res_auth = it_head_client.post(
        f"/api/v1/superadmin/purge/requests/{purge_id}/authorize/",
        {"action": "APPROVE"},
        format="json",
    )
    assert res_auth.status_code == 200
    assert res_auth.data["status"] == "AUTHORIZED"

    archive.refresh_from_db()
    assert archive.status == "PURGED"


def test_dashboard_metrics(stub_iam):
    client = _client(stub_iam)
    res = client.get("/api/v1/superadmin/dashboard/")
    assert res.status_code == 200
    assert "total_users" in res.data
    assert "active_users" in res.data
