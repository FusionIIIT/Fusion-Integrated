"""Privilege escalation and role boundary enforcement tests for FTS."""
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from modules.fts.services.files import create_file
from modules.fts.tests.conftest import make_fts_session as make_session

pytestmark = pytest.mark.django_db


def test_student_cannot_access_fts(stub_iam):
    """BR-FTS-001: Students cannot access FTS operational endpoints."""
    stub_iam(
        make_session(
            user_id=5001,
            kind="student",
            roles=("student",),
            active_role="student",
            modules=(),
            permissions=(),
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token student-token")

    res = c.get("/api/v1/fts/inbox/")
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_admin_cannot_perform_operational_file_actions(admin_client):
    """BR-FTS-001, BR-FTS-010: System administrators cannot perform operational file actions."""
    admin = admin_client()

    # Admin cannot create operational file
    res_create = admin.post(
        "/api/v1/fts/files/",
        data={"subject": "Admin file", "comment": "Admin trying to create."},
        format="json",
    )
    assert res_create.status_code == status.HTTP_403_FORBIDDEN


def test_employee_without_governance_permission_cannot_view_audit_logs(fts_client):
    """BR-FTS-010, BR-FTS-011: Audit log access requires explicit governance permission."""
    employee = fts_client(user_id=101, permissions=("fts.file.view", "fts.file.create"))
    res = employee.get("/api/v1/fts/governance/audit-logs/")
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_non_owner_cannot_archive_file(fts_client):
    """BR-FTS-010, BR-FTS-012: Only file owner can archive a circulated file."""
    file_obj = create_file(
        subject="Confidential Project",
        comment_text="Owner file.",
        actor_user_id=101,
        actor_username="owner_fac",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_member",
        recipient_role="Junior Assistant",
    )
    non_owner = fts_client(user_id=202, permissions=("fts.file.archive", "fts.file.view"))
    res = non_owner.post(f"/api/v1/fts/files/{file_obj.id}/archive/")
    assert res.status_code == status.HTTP_403_FORBIDDEN
