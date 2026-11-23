"""Privilege escalation and permission enforcement tests for BADMS endpoints."""
import pytest
from django.conf import settings
from rest_framework.test import APIClient

from conftest import make_session

pytestmark = pytest.mark.django_db


def _client(stub_iam, **kw):
    stub_iam(make_session(**kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def test_unauthenticated_requests_fail_with_401():
    c = APIClient()
    endpoints = [
        ("GET", "/api/v1/badms/backups/"),
        ("POST", "/api/v1/badms/backups/manual/"),
        ("GET", "/api/v1/badms/schedules/"),
        ("POST", "/api/v1/badms/schedules/"),
        ("GET", "/api/v1/badms/archival-requests/"),
        ("POST", "/api/v1/badms/archival-requests/"),
        ("GET", "/api/v1/badms/storage-extensions/"),
        ("POST", "/api/v1/badms/storage-extensions/"),
        ("GET", "/api/v1/badms/restorations/"),
        ("POST", "/api/v1/badms/restorations/"),
        ("GET", "/api/v1/badms/audit-logs/"),
        ("GET", "/api/v1/badms/security-policies/"),
    ]
    for method, path in endpoints:
        res = c.get(path) if method == "GET" else c.post(path, {})
        assert (
            res.status_code == 401
        ), f"{path} did not reject unauthenticated request with 401 (got {res.status_code})"


def test_caller_without_badms_module_grant_refused_with_403(stub_iam):
    # Principal has general session credentials but no BADMS module grant
    c = _client(
        stub_iam,
        user_id=1001,
        kind="student",
        modules=(),  # Lacks badms module grant
        permissions=("badms.backup.view",),
    )
    res = c.get("/api/v1/badms/backups/")
    assert res.status_code == 403
    res_post = c.post("/api/v1/badms/archival-requests/", {})
    assert res_post.status_code == 403


def test_student_cannot_trigger_manual_backup(stub_iam):
    c = _client(
        stub_iam,
        user_id=1001,
        kind="student",
        modules=("badms",),
        permissions=("badms.backup.view",),  # lacks badms.backup.manage
    )
    res = c.post("/api/v1/badms/backups/manual/", {"dataset_name": "default"})
    assert res.status_code == 403


def test_student_cannot_approve_archival(stub_iam):
    c = _client(
        stub_iam,
        user_id=1001,
        kind="student",
        modules=("badms",),
        permissions=("badms.archival.view", "badms.archival.create"),
    )
    res = c.post("/api/v1/badms/archival-requests/1/decide/", {"decision": "approve"})
    assert res.status_code == 403


def test_student_cannot_decide_storage_extension(stub_iam):
    c = _client(
        stub_iam,
        user_id=1001,
        kind="student",
        modules=("badms",),
        permissions=("badms.storage.view", "badms.storage.create"),  # lacks badms.storage.approve
    )
    res = c.post("/api/v1/badms/storage-extensions/1/decide/", {"decision": "approve"})
    assert res.status_code == 403


def test_faculty_cannot_classify_data(stub_iam):
    c = _client(
        stub_iam,
        user_id=2001,
        kind="faculty",
        modules=("badms",),
        permissions=("badms.archival.view", "badms.archival.create"),
    )
    res = c.post("/api/v1/badms/archival-requests/1/classify/", {"classification": "Sensitive"})
    assert res.status_code == 403


def test_sysadmin_cannot_configure_encryption_without_security_role(stub_iam):
    c = _client(
        stub_iam,
        user_id=3001,
        kind="staff",
        roles=("SysAdmin",),
        active_role="SysAdmin",
        modules=("badms",),
        permissions=("badms.archival.view", "badms.archival.review"),
    )
    res = c.post(
        "/api/v1/badms/archival-requests/1/configure-encryption/",
        {"encryption_algorithm": "AES-256-GCM"},
    )
    assert res.status_code == 403


def test_faculty_cannot_execute_technical_restoration(stub_iam):
    c = _client(
        stub_iam,
        user_id=4001,
        kind="faculty",
        modules=("badms",),
        permissions=("badms.restoration.view", "badms.restoration.create"),
    )
    res = c.post("/api/v1/badms/restorations/1/execute/", {})
    assert res.status_code == 403


def test_non_superadmin_cannot_perform_special_archival(stub_iam):
    c = _client(
        stub_iam,
        user_id=6001,
        kind="staff",
        roles=("SysAdmin",),
        active_role="SysAdmin",
        modules=("badms",),
        permissions=("badms.archival.view", "badms.archival.review"),
    )
    res = c.post(
        "/api/v1/badms/archival-requests/special/",
        {
            "department": "CSE",
            "file_name": "special_dump.sql",
            "file_type": "database",
            "file_size_bytes": 1000,
            "reason": "Accreditation snapshot",
            "file_storage_path": "/tmp/special",
        },
    )
    assert res.status_code == 403


def test_cookie_write_without_csrf_token_answers_403(stub_iam):
    stub_iam(
        make_session(
            user_id=1001,
            kind="student",
            modules=("badms",),
            permissions=("badms.storage.create",),
        )
    )
    c = APIClient()
    c.cookies[settings.IAM_AUTH_COOKIE_NAME] = "test-session-cookie"
    # POST write with cookie but omitting HTTP_X_CSRF_TOKEN
    res = c.post(
        "/api/v1/badms/storage-extensions/",
        {"requested_extension_bytes": 1024, "justification": "Test project files"},
        format="json",
    )
    assert res.status_code == 403


def test_student_refused_backup_and_schedule_endpoints_with_403(stub_iam):
    """Regression test: Student lacking badms.backup.view must receive 403 on restricted backup endpoints."""
    c = _client(
        stub_iam,
        user_id=1001,
        kind="student",
        modules=("badms",),
        permissions=(
            "badms.archival.view",
            "badms.archival.create",
            "badms.storage.view",
            "badms.storage.create",
            "badms.restoration.view",
            "badms.restoration.create",
        ),
    )
    # GET /api/v1/badms/backups/
    res_backups = c.get("/api/v1/badms/backups/")
    assert res_backups.status_code == 403, f"Expected 403 Forbidden, got {res_backups.status_code}"

    # GET /api/v1/badms/backups/1/
    res_backup_detail = c.get("/api/v1/badms/backups/1/")
    assert res_backup_detail.status_code == 403, f"Expected 403 Forbidden, got {res_backup_detail.status_code}"

    # GET /api/v1/badms/schedules/
    res_schedules = c.get("/api/v1/badms/schedules/")
    assert res_schedules.status_code == 403, f"Expected 403 Forbidden, got {res_schedules.status_code}"

