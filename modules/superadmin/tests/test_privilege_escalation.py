"""Every write endpoint returns 403 for a principal without the required permission."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.superadmin.domain.constants import (
    ARCHIVAL_STATUS_REVERSIBLE,
    PURGE_STATUS_APPROVED,
    PURGE_STATUS_PENDING_IT_HEAD,
)
from modules.superadmin.models.archival import (
    ArchivedUserRecord,
    HistoricalDataArchive,
    PurgeRequest,
)

pytestmark = pytest.mark.django_db


def _client(stub_iam, permissions, uid=999):
    stub_iam(
        make_session(
            user_id=uid,
            kind="staff",
            permissions=permissions,
            modules=("superadmin",),
            active_role="student",
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def _archived_user(uid=5000):
    return ArchivedUserRecord.objects.create(
        user_id=uid,
        institute_id="2020BCS001",
        username=f"u{uid}",
        email=f"u{uid}@iiitdmj.ac.in",
        user_kind="student",
        status=ARCHIVAL_STATUS_REVERSIBLE,
        archived_at=timezone.now() - timedelta(days=5),
        reversible_until=timezone.now() + timedelta(days=25),
        authorized_by=1,
        archival_reason="Test.",
    )


def _archive():
    today = date.today()
    return HistoricalDataArchive.objects.create(
        dataset_category="academics",
        title="Old dataset",
        date_range_start=today - timedelta(days=800),
        date_range_end=today - timedelta(days=400),
        record_count=100,
        backup_file_path="/b/x.tar.gz",
        backup_checksum="abc",
        retention_expires_at=today - timedelta(days=10),
        archived_by=1,
    )


# -- Dashboard (view only) ------------------------------------------------


def test_dashboard_requires_view_permission(stub_iam):
    client = _client(stub_iam, permissions=())
    assert client.get("/api/v1/superadmin/dashboard/").status_code == 403


# -- Archival: add requires superadmin.archival.add -----------------------


def test_archive_user_requires_add_permission(stub_iam):
    # Has view but not add
    client = _client(stub_iam, ("superadmin.archival.view",))
    response = client.post(
        "/api/v1/superadmin/archival/users/",
        {
            "user_id": 7001,
            "institute_id": "2021BCS001",
            "username": "u7001",
            "email": "u7001@iiitdmj.ac.in",
            "user_kind": "student",
            "is_deactivated": True,
            "deactivated_at": "2026-01-01T00:00:00Z",
            "has_pending_transactions": False,
            "archival_reason": "Graduated.",
        },
        format="json",
    )
    assert response.status_code == 403


def test_restore_user_requires_change_permission(stub_iam):
    record = _archived_user(5001)
    # Has view but not change
    client = _client(stub_iam, ("superadmin.archival.view",))
    response = client.post(
        f"/api/v1/superadmin/archival/users/{record.user_id}/restore/",
        {"restoration_reason": "Rejoining."},
        format="json",
    )
    assert response.status_code == 403


# -- Purge: initiate requires superadmin.purge.add ------------------------


def test_create_purge_request_requires_add_permission(stub_iam):
    archive = _archive()
    client = _client(stub_iam, ("superadmin.purge.view",))
    response = client.post(
        "/api/v1/superadmin/purge/requests/",
        {
            "archive_id": archive.pk,
            "request_reason": "Retention lapsed.",
        },
        format="json",
    )
    assert response.status_code == 403


# -- Purge: authorize requires superadmin.purge.change --------------------


def test_decide_purge_requires_change_permission(stub_iam):
    archive = _archive()
    req = PurgeRequest.objects.create(
        archive=archive,
        status=PURGE_STATUS_PENDING_IT_HEAD,
        requested_by=1,
        request_reason="Need decision.",
    )
    # Has view and add but not change
    client = _client(stub_iam, ("superadmin.purge.view", "superadmin.purge.add"))
    response = client.post(
        f"/api/v1/superadmin/purge/requests/{req.pk}/decision/",
        {"approve": True, "comments": ""},
        format="json",
    )
    assert response.status_code == 403


# -- Purge: execute requires superadmin.purge.add -------------------------


def test_execute_purge_requires_add_permission(stub_iam):
    archive = _archive()
    req = PurgeRequest.objects.create(
        archive=archive,
        status=PURGE_STATUS_APPROVED,
        requested_by=1,
        request_reason="Approved.",
        it_head_id=200,
        it_head_decision_at=timezone.now(),
    )
    client = _client(stub_iam, ("superadmin.purge.view",))
    response = client.post(
        f"/api/v1/superadmin/purge/requests/{req.pk}/execute/",
        {},
        format="json",
    )
    assert response.status_code == 403


# -- Policy: change requires superadmin.policy.change --------------------


def test_supersede_policy_requires_change_permission(stub_iam):
    client = _client(stub_iam, ("superadmin.policy.view",))
    response = client.post(
        "/api/v1/superadmin/policy/parameters/",
        {
            "key": "archival.reversibility_window_days",
            "value": "45",
        },
        format="json",
    )
    assert response.status_code == 403


# -- Audit: view requires superadmin.audit.view ---------------------------


def test_audit_log_list_requires_view_permission(stub_iam):
    client = _client(stub_iam, permissions=())
    assert client.get("/api/v1/superadmin/audit/logs/").status_code == 403


# -- IT Head cannot initiate purge (no purge.add) -------------------------


def test_it_head_cannot_initiate_purge(stub_iam):
    from modules.superadmin.tests.conftest import IT_PERMS

    archive = _archive()
    client = _client(stub_iam, IT_PERMS, uid=200)
    response = client.post(
        "/api/v1/superadmin/purge/requests/",
        {
            "archive_id": archive.pk,
            "request_reason": "IT Head attempting initiate.",
        },
        format="json",
    )
    # IT Head lacks purge.add — should be 403
    assert response.status_code == 403
