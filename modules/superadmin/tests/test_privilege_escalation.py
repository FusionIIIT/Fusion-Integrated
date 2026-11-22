"""Tests ensuring privilege boundaries, RBAC closed verbs, and separation of duties."""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.superadmin.models import HistoricalArchiveRecord, PurgeRequestRecord

pytestmark = pytest.mark.django_db


def test_student_cannot_access_superadmin_endpoints(stub_iam):
    # A standard student without superadmin module grant or permissions
    stub_iam(make_session(user_id=8001, kind="student", permissions=(), modules=()))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token tok-student")

    res = client.get("/api/v1/superadmin/users/")
    assert res.status_code == 403

    res2 = client.get("/api/v1/superadmin/dashboard/")
    assert res2.status_code == 403

    res3 = client.get("/api/v1/superadmin/roles/")
    assert res3.status_code == 403


def test_read_only_admin_cannot_mutate_users(stub_iam):
    # User holds only view permission, not write
    stub_iam(
        make_session(
            user_id=8002,
            kind="staff",
            permissions=("superadmin.user.view",),
            modules=("superadmin",),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token tok-staff")

    # GET succeeds
    res_get = client.get("/api/v1/superadmin/users/")
    assert res_get.status_code == 200

    # POST create fails with 403
    res_post = client.post(
        "/api/v1/superadmin/users/",
        {
            "user_id": 8003,
            "institute_id": "24BCS803",
            "email": "u8003@iiitdmj.ac.in",
            "user_type": "STUDENT",
        },
        format="json",
    )
    assert res_post.status_code == 403


def test_purge_separation_of_duties_prevents_self_authorization(stub_iam):
    # Super Admin creates purge request
    admin_id = 9001
    stub_iam(
        make_session(
            user_id=admin_id,
            kind="staff",
            permissions=("superadmin.purge.create", "superadmin.purge.approve"),
            modules=("superadmin",),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token tok-admin", HTTP_X_STEP_UP_AUTH="verified")

    archive = HistoricalArchiveRecord.objects.create(
        entity_type="LEGACY_RECORDS",
        record_identifier="REC_999",
        payload={},
        retention_period_days=365,
        purge_eligible_at=timezone.now() - timedelta(days=5),
        status="ACTIVE_ARCHIVE",
        archived_by_user_id=admin_id,
    )

    purge_req = PurgeRequestRecord.objects.create(
        archive_record=archive,
        requested_by_user_id=admin_id,
        request_reason="Retention expired",
        status="REQUESTED",
    )

    # Attempt to self-authorize MUST fail (ConflictError / 409)
    res_auth = client.post(
        f"/api/v1/superadmin/purge/requests/{purge_req.id}/authorize/",
        {"action": "APPROVE"},
        format="json",
    )
    assert res_auth.status_code == 409
    assert "Separation of duties" in str(res_auth.data)
