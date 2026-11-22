"""Privilege escalation tests for System Admin module endpoints.

Verifies that users lacking required permissions are refused with 403,
users without module grant are refused, and bad inputs fail cleanly with 400.
"""
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.system_admin.models import UserAccount

pytestmark = pytest.mark.django_db


def _client_with_perms(stub_iam, uid=1001, perms=(), modules=("system_admin",)):
    stub_iam(
        make_session(
            user_id=uid,
            kind="staff",
            modules=modules,
            permissions=perms,
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token mock-token")
    return c


def test_user_without_module_grant_is_refused(stub_iam):
    client = _client_with_perms(stub_iam, perms=("system_admin.user.view",), modules=())
    res = client.get("/api/v1/system_admin/users/")
    assert res.status_code == 403


def test_read_only_user_cannot_deactivate_account(stub_iam):
    account = UserAccount.objects.create(
        user_id=2001,
        institute_id="USER2001",
        username="user2001",
        email="user2001@example.com",
        user_type="student",
        status="active",
    )
    client = _client_with_perms(stub_iam, perms=("system_admin.user.view",))
    res = client.post(
        f"/api/v1/system_admin/users/{account.user_id}/status/",
        {"action": "deactivate", "reason": "Test deactivation"},
    )
    assert res.status_code == 403
    account.refresh_from_db()
    assert account.status == "active"


def test_read_only_user_cannot_assign_roles(stub_iam):
    client = _client_with_perms(stub_iam, perms=("system_admin.role.view",))
    res = client.post(
        "/api/v1/system_admin/roles/assign/",
        {
            "user_id": 2002,
            "role_code": "faculty",
            "start_date": "2026-01-01T00:00:00Z",
        },
    )
    assert res.status_code == 403


def test_read_only_user_cannot_initiate_purge(stub_iam):
    client = _client_with_perms(stub_iam, perms=("system_admin.archive.view",))
    res = client.post(
        "/api/v1/system_admin/archives/purge-request/",
        {"dataset_identifier": "rec-999", "retention_years": 7, "reason": "Test purge"},
    )
    assert res.status_code == 403


def test_read_only_user_cannot_update_system_config(stub_iam):
    client = _client_with_perms(stub_iam, perms=("system_admin.user.view",))
    res = client.patch(
        "/api/v1/system_admin/config/",
        {"parameters": {"bulk_operation_limit": "500"}},
        format="json",
    )
    assert res.status_code == 403


def test_bad_input_returns_400_not_500(stub_iam):
    client = _client_with_perms(stub_iam, perms=("system_admin.user.add",))
    res = client.post(
        "/api/v1/system_admin/users/create/",
        {"user_id": "not-an-int", "email": "invalid-email"},
    )
    assert res.status_code == 400


def test_admin_with_full_perms_can_perform_actions(stub_iam):
    perms = (
        "system_admin.user.view",
        "system_admin.user.add",
        "system_admin.user.change",
        "system_admin.role.manage",
        "system_admin.config.change",
    )
    client = _client_with_perms(stub_iam, perms=perms)
    res = client.post(
        "/api/v1/system_admin/users/create/",
        {
            "user_id": 2005,
            "institute_id": "FAC2005",
            "username": "user2005",
            "email": "user2005@iiitdmj.ac.in",
            "user_type": "faculty",
            "department": "CSE",
        },
    )
    assert res.status_code == 201
