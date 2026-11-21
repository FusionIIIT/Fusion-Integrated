"""N+1 query budget checks for superadmin list endpoints."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.superadmin.domain.constants import (
    ARCHIVAL_STATUS_REVERSIBLE,
)
from modules.superadmin.models.archival import (
    ArchivedUserRecord,
    HistoricalDataArchive,
)
from modules.superadmin.models.audit import SuperAdminAuditLog
from modules.superadmin.models.config import SystemPolicyParameter

pytestmark = pytest.mark.django_db

SA_PERMS = (
    "superadmin.dashboard.view",
    "superadmin.archival.view",
    "superadmin.archival.add",
    "superadmin.archival.change",
    "superadmin.purge.view",
    "superadmin.purge.add",
    "superadmin.policy.view",
    "superadmin.policy.change",
    "superadmin.audit.view",
)


def _client(stub_iam, uid=100):
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


def _make_archived_users(n: int):
    for i in range(n):
        uid = 1000 + i
        ArchivedUserRecord.objects.get_or_create(
            user_id=uid,
            defaults={
                "institute_id": f"2020BCS{i:03d}",
                "username": f"u{uid}",
                "email": f"u{uid}@iiitdmj.ac.in",
                "user_kind": "student",
                "status": ARCHIVAL_STATUS_REVERSIBLE,
                "archived_at": timezone.now() - timedelta(days=10),
                "reversible_until": timezone.now() + timedelta(days=20),
                "authorized_by": 1,
                "archival_reason": "Graduated.",
            },
        )


def _make_archives(n: int):
    archives = []
    today = date.today()
    for i in range(n):
        a = HistoricalDataArchive.objects.create(
            dataset_category=f"cat{i}",
            title=f"Dataset {i}",
            date_range_start=today - timedelta(days=400 + i),
            date_range_end=today - timedelta(days=200 + i),
            record_count=100,
            backup_file_path=f"/b/{i}.tar.gz",
            backup_checksum=f"ck{i}",
            retention_expires_at=today - timedelta(days=1),
            archived_by=1,
        )
        archives.append(a)
    return archives


def _make_policy_params(n: int):
    for i in range(n):
        SystemPolicyParameter.objects.get_or_create(
            key=f"test.param_{i}",
            version=1,
            defaults={
                "value": str(i),
                "updated_by": 1,
            },
        )


def _make_audit_logs(n: int):
    for i in range(n):
        # Use insert via base save to bypass immutability guard
        from django.db import models as _orm

        entry = SuperAdminAuditLog(
            actor_id=1,
            actor_username="admin",
            actor_role="super_admin",
            action="archival.user.created",
            target_id=str(i),
            target_type="user",
            reason="Budget test.",
        )
        _orm.Model.save(entry)


@pytest.mark.parametrize(
    ("path", "budget", "setup"),
    [
        ("/api/v1/superadmin/archival/users/", 3, lambda: _make_archived_users(5)),
        ("/api/v1/superadmin/audit/logs/", 3, lambda: _make_audit_logs(5)),
        ("/api/v1/superadmin/policy/parameters/", 3, lambda: _make_policy_params(3)),
    ],
)
def test_list_endpoint_stays_within_budget(
    stub_iam, django_assert_max_num_queries, path, budget, setup
):
    setup()
    client = _client(stub_iam)
    with django_assert_max_num_queries(budget):
        resp = client.get(path)
    assert resp.status_code == 200


def test_archived_user_list_count_does_not_grow_with_rows(stub_iam):
    """Five more rows — same number of queries. N+1 shows up here."""
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    client = _client(stub_iam)
    _make_archived_users(3)

    with CaptureQueriesContext(connection) as first:
        client.get("/api/v1/superadmin/archival/users/")

    _make_archived_users(6)  # Creates users 1003..1005

    with CaptureQueriesContext(connection) as second:
        client.get("/api/v1/superadmin/archival/users/")

    assert len(second) <= len(first) + 1, (
        f"{len(first)} queries for 3 rows, {len(second)} for 6 rows — possible N+1"
    )
