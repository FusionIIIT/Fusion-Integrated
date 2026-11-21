"""Privilege escalation and role boundary tests (BR-FTS-001, AFR-FTS-009)."""
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from conftest import make_session
from modules.fts.services import file_service

pytestmark = pytest.mark.django_db


def test_system_admin_blocked_from_creating_files(stub_iam):
    session = make_session(
        user_id=1,
        kind="admin",
        active_role="system_admin",
        roles=["system_admin"],
        permissions=["fts.file.create", "fts.file.view"],
        modules=["fts"],
    )
    stub_iam(session=session)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token admin-token")

    resp = client.post(
        "/api/v1/fts/files/",
        {
            "subject": "Admin Operational File",
            "initial_comment": "Attempting operational file creation.",
            "is_draft": False,
            "receiver_id": 102,
        },
        format="json",
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_student_blocked_from_file_operations(stub_iam):
    session = make_session(
        user_id=5001,
        kind="student",
        active_role="student",
        roles=["student"],
        permissions=[],
        modules=["fts"],
    )
    stub_iam(session=session)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token student-token")

    resp = client.post(
        "/api/v1/fts/files/",
        {
            "subject": "Student Proposal",
            "initial_comment": "Student note.",
            "is_draft": True,
        },
        format="json",
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_non_holder_forbidden_from_forwarding_file(stub_iam):
    f = file_service.create_file(
        subject="Staff Note",
        initial_comment="Init.",
        creator_id=101,
        receiver_id=102,
    )

    session = make_session(
        user_id=101,
        kind="faculty",
        permissions=["fts.file.update", "fts.file.view"],
        modules=["fts"],
    )
    stub_iam(session=session)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token faculty-token")

    resp = client.post(
        f"/api/v1/fts/files/{f.file_id}/forward/",
        {"receiver_id": 103, "remarks": "Unauthorized forward attempt."},
        format="json",
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN
