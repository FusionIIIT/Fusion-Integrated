"""Query budget tests for Super Admin list endpoints to ensure N+1 prevention."""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.superadmin.models import (
    HistoricalArchiveRecord,
    RoleAssignmentRecord,
    UserAccountRecord,
)

pytestmark = pytest.mark.django_db

ALL_PERMS = (
    "superadmin.user.view",
    "superadmin.role.view",
    "superadmin.archive.view",
    "superadmin.audit_log.view",
)


def _client(stub_iam):
    stub_iam(
        make_session(
            user_id=1,
            kind="staff",
            permissions=ALL_PERMS,
            modules=("superadmin",),
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token tok-123")
    return c


def test_user_list_query_budget(stub_iam, django_assert_num_queries):
    client = _client(stub_iam)

    for i in range(15):
        UserAccountRecord.objects.create(
            user_id=1000 + i,
            institute_id=f"24BCS{1000 + i}",
            email=f"u{1000 + i}@iiitdmj.ac.in",
            user_type="STUDENT",
            activation_status="ACTIVE",
        )

    # List query should be bounded and constant
    with django_assert_num_queries(1):
        res = client.get("/api/v1/superadmin/users/")
        assert res.status_code == 200
        assert len(res.data) >= 15


def test_roles_list_query_budget(stub_iam, django_assert_num_queries):
    client = _client(stub_iam)
    now = timezone.now()

    for i in range(10):
        RoleAssignmentRecord.objects.create(
            user_id=2000 + i,
            role_name="Course Instructor",
            valid_from=now,
            status="ACTIVE",
            assigned_by_user_id=1,
        )

    with django_assert_num_queries(1):
        res = client.get("/api/v1/superadmin/roles/")
        assert res.status_code == 200
        assert len(res.data) >= 10


def test_archive_list_query_budget(stub_iam, django_assert_num_queries):
    client = _client(stub_iam)
    now = timezone.now()

    for i in range(10):
        HistoricalArchiveRecord.objects.create(
            entity_type="DATA",
            record_identifier=f"REC_{i}",
            payload={},
            retention_period_days=365,
            purge_eligible_at=now + timedelta(days=365),
            status="ACTIVE_ARCHIVE",
            archived_by_user_id=1,
        )

    with django_assert_num_queries(1):
        res = client.get("/api/v1/superadmin/archive/")
        assert res.status_code == 200
        assert len(res.data) >= 10
