"""API views coverage for superadmin endpoints."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.superadmin.models.archival import (
    ArchivedUserRecord,
)
from modules.superadmin.tests.conftest import SA_PERMS

pytestmark = pytest.mark.django_db


def _sa_client(stub_iam, uid=100):
    stub_iam(
        make_session(
            user_id=uid,
            kind="staff",
            roles=("super_admin",),
            active_role="super_admin",
            permissions=SA_PERMS,
            modules=("superadmin",),
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def test_dashboard_api(stub_iam):
    client = _sa_client(stub_iam)
    resp = client.get("/api/v1/superadmin/dashboard/")
    assert resp.status_code == 200
    data = resp.json()
    assert "archived_users_total" in data
    assert "purge_requests_pending" in data


def test_archived_user_detail_api(stub_iam):
    client = _sa_client(stub_iam)
    record = ArchivedUserRecord.objects.create(
        user_id=9001,
        institute_id="2020BCS901",
        username="u9001",
        email="u9001@iiitdmj.ac.in",
        user_kind="student",
        status="reversible",
        archived_at=timezone.now(),
        reversible_until=timezone.now() + timedelta(days=30),
        authorized_by=1,
        archival_reason="Graduated.",
    )
    resp = client.get(f"/api/v1/superadmin/archival/users/{record.user_id}/")
    assert resp.status_code == 200
    assert resp.json()["username"] == "u9001"

    # Non-existent user returns 404
    resp_404 = client.get("/api/v1/superadmin/archival/users/99999/")
    assert resp_404.status_code == 404


def test_historical_archive_list_and_create_api(stub_iam):
    client = _sa_client(stub_iam)
    today = date.today()
    payload = {
        "dataset_category": "examination",
        "title": "Exam Archive 2024",
        "date_range_start": str(today - timedelta(days=365)),
        "date_range_end": str(today - timedelta(days=180)),
        "record_count": 50,
        "backup_file_path": "/backups/exam2024.tar.gz",
        "backup_checksum": "sha256abc",
        "retention_expires_at": str(today + timedelta(days=365)),
    }
    resp = client.post("/api/v1/superadmin/archival/history/", payload, format="json")
    assert resp.status_code == 201
    archive_id = resp.json()["id"]

    list_resp = client.get("/api/v1/superadmin/archival/history/")
    assert list_resp.status_code == 200
    assert len(list_resp.json()["results"]) >= 1

    # Restore historical archive
    restore_resp = client.post(f"/api/v1/superadmin/archival/history/{archive_id}/restore/", {})
    assert restore_resp.status_code == 200
    assert restore_resp.json()["is_restored"] is True


def test_audit_log_export_csv_api(stub_iam):
    client = _sa_client(stub_iam)
    resp = client.get("/api/v1/superadmin/audit/export/")
    assert resp.status_code == 200
    assert resp["Content-Type"] == "text/csv"
    assert "attachment; filename=" in resp["Content-Disposition"]
