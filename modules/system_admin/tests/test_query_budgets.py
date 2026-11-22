"""Query count budget tests for System Admin list endpoints."""
import datetime

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.system_admin.models import RoleAssignment, SystemAuditLog, UserAccount

pytestmark = pytest.mark.django_db

ADMIN_PERMS = (
    "system_admin.user.view",
    "system_admin.role.view",
    "system_admin.archive.view",
    "system_admin.audit.view",
    "system_admin.config.view",
)


def _client(stub_iam, perms=ADMIN_PERMS):
    stub_iam(
        make_session(
            user_id=1,
            kind="staff",
            modules=("system_admin",),
            permissions=perms,
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token mock-token")
    return c


def test_users_list_query_budget(stub_iam, django_assert_num_queries):
    client = _client(stub_iam)
    for i in range(5):
        UserAccount.objects.create(
            user_id=3000 + i,
            institute_id=f"BUDGET_{i}",
            username=f"budget_user_{i}",
            email=f"budget_{i}@example.com",
            user_type="student",
            status="active",
        )

    with django_assert_num_queries(2):
        res1 = client.get("/api/v1/system_admin/users/")
        assert res1.status_code == 200

    for i in range(5, 15):
        UserAccount.objects.create(
            user_id=3000 + i,
            institute_id=f"BUDGET_{i}",
            username=f"budget_user_{i}",
            email=f"budget_{i}@example.com",
            user_type="student",
            status="active",
        )

    with django_assert_num_queries(2):
        res2 = client.get("/api/v1/system_admin/users/")
        assert res2.status_code == 200


def test_roles_list_query_budget(stub_iam, django_assert_num_queries):
    client = _client(stub_iam)
    today = datetime.date(2026, 1, 1)
    for i in range(5):
        RoleAssignment.objects.create(
            user_id=4000 + i,
            role_code="faculty",
            status="active",
            start_date=today,
            reason="budget test",
            assigned_by=1,
        )

    with django_assert_num_queries(1):
        res1 = client.get("/api/v1/system_admin/roles/")
        assert res1.status_code == 200

    for i in range(5, 15):
        RoleAssignment.objects.create(
            user_id=4000 + i,
            role_code="faculty",
            status="active",
            start_date=today,
            reason="budget test",
            assigned_by=1,
        )

    with django_assert_num_queries(1):
        res2 = client.get("/api/v1/system_admin/roles/")
        assert res2.status_code == 200


def test_audit_logs_list_query_budget(stub_iam, django_assert_num_queries):
    client = _client(stub_iam)
    for i in range(5):
        SystemAuditLog.objects.create(
            actor_id=1,
            action="TEST_ACTION",
            target_id=str(i),
        )

    with django_assert_num_queries(2):
        res1 = client.get("/api/v1/system_admin/audit/")
        assert res1.status_code == 200

    for i in range(5, 15):
        SystemAuditLog.objects.create(
            actor_id=1,
            action="TEST_ACTION",
            target_id=str(i),
        )

    with django_assert_num_queries(2):
        res2 = client.get("/api/v1/system_admin/audit/")
        assert res2.status_code == 200
