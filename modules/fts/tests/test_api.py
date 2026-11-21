"""API integration tests for FTS endpoints."""
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from conftest import make_session
from modules.fts.services import file_service

pytestmark = pytest.mark.django_db

EMPLOYEE_PERMS = [
    "fts.file.view",
    "fts.file.create",
    "fts.file.update",
    "fts.file.delete",
    "fts.file.manage",
]


def test_inbox_api(stub_iam):
    session = make_session(
        user_id=102,
        kind="faculty",
        permissions=EMPLOYEE_PERMS,
        modules=["fts"],
    )
    stub_iam(session=session)

    file_service.create_file(
        subject="Inbox Target File",
        initial_comment="Need your review.",
        creator_id=101,
        receiver_id=102,
    )

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token valid-token")
    resp = client.get("/api/v1/fts/inbox/")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["subject"] == "Inbox Target File"


def test_create_file_api(stub_iam):
    session = make_session(
        user_id=101,
        kind="staff",
        permissions=EMPLOYEE_PERMS,
        modules=["fts"],
    )
    stub_iam(session=session)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token valid-token")
    payload = {
        "subject": "New Operational File",
        "description": "File created via API.",
        "initial_comment": "First remark.",
        "is_draft": False,
        "receiver_id": 102,
    }
    resp = client.post("/api/v1/fts/files/", payload, format="json")
    assert resp.status_code == status.HTTP_201_CREATED
    data = resp.json()
    assert data["subject"] == "New Operational File"
    assert data["status"] == "circulating"


def test_file_detail_404_for_unassociated_user(stub_iam):
    f = file_service.create_file(
        subject="Private Dean File",
        initial_comment="Confidential.",
        creator_id=101,
        receiver_id=102,
    )

    session = make_session(
        user_id=999,
        kind="faculty",
        permissions=EMPLOYEE_PERMS,
        modules=["fts"],
    )
    stub_iam(session=session)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token valid-token")
    resp = client.get(f"/api/v1/fts/files/{f.file_id}/")
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_forward_and_return_flow(stub_iam):
    f = file_service.create_file(
        subject="Multi-hop Workflow",
        initial_comment="Hop 1.",
        creator_id=101,
        receiver_id=102,
    )

    # Actor 102 forwards to 103
    session_102 = make_session(
        user_id=102,
        kind="faculty",
        permissions=EMPLOYEE_PERMS,
        modules=["fts"],
    )
    stub_iam(session=session_102)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token token-102")

    resp_fwd = client.post(
        f"/api/v1/fts/files/{f.file_id}/forward/",
        {"receiver_id": 103, "remarks": "Forwarding to 103."},
        format="json",
    )
    assert resp_fwd.status_code == status.HTTP_200_OK

    # Actor 103 returns to previous sender (102)
    session_103 = make_session(
        user_id=103,
        kind="staff",
        permissions=EMPLOYEE_PERMS,
        modules=["fts"],
    )
    stub_iam(session=session_103)
    client.credentials(HTTP_AUTHORIZATION="Token token-103")

    resp_ret = client.post(
        f"/api/v1/fts/files/{f.file_id}/return/",
        {"remarks": "Returning back to 102."},
        format="json",
    )
    assert resp_ret.status_code == status.HTTP_200_OK
    assert resp_ret.json()["action"] == "returned"


def test_outbox_api(stub_iam):
    session = make_session(
        user_id=101,
        kind="faculty",
        permissions=EMPLOYEE_PERMS,
        modules=["fts"],
    )
    stub_iam(session=session)

    file_service.create_file(
        subject="Outbox Test File",
        initial_comment="Moving out.",
        creator_id=101,
        receiver_id=102,
    )

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token token-101")
    resp = client.get("/api/v1/fts/outbox/")
    assert resp.status_code == status.HTTP_200_OK
    assert len(resp.json()) >= 1


def test_draft_edit_and_discard_api(stub_iam):
    session = make_session(
        user_id=101,
        kind="staff",
        permissions=EMPLOYEE_PERMS,
        modules=["fts"],
    )
    stub_iam(session=session)

    draft = file_service.create_file(
        subject="Draft to Edit",
        initial_comment="Draft note.",
        creator_id=101,
        is_draft=True,
    )

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token token-101")

    # Edit draft
    patch_resp = client.patch(
        f"/api/v1/fts/files/{draft.file_id}/draft/",
        {"subject": "Updated Draft Subject", "comment": "Updated comment."},
        format="json",
    )
    assert patch_resp.status_code == status.HTTP_200_OK
    assert patch_resp.json()["subject"] == "Updated Draft Subject"

    # Discard draft
    del_resp = client.delete(f"/api/v1/fts/files/{draft.file_id}/draft/")
    assert del_resp.status_code == status.HTTP_204_NO_CONTENT


def test_archive_file_api(stub_iam):
    f = file_service.create_file(
        subject="File To Archive",
        initial_comment="Work complete.",
        creator_id=101,
        receiver_id=102,
        is_draft=False,
    )
    # Return file to owner 101 so owner is holder
    file_service.return_file(
        file_id_or_pk=f.file_id,
        sender_id=102,
        remarks="Returned to owner for archival.",
    )

    session = make_session(
        user_id=101,
        kind="faculty",
        permissions=EMPLOYEE_PERMS,
        modules=["fts"],
    )
    stub_iam(session=session)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token token-101")

    resp = client.post(
        f"/api/v1/fts/files/{f.file_id}/archive/",
        {"remarks": "Archiving file."},
        format="json",
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["status"] == "archived"


def test_audit_logs_api(stub_iam):
    session = make_session(
        user_id=1,
        kind="admin",
        active_role="system_admin",
        roles=["system_admin"],
        permissions=["fts.audit.view"],
        modules=["fts"],
    )
    stub_iam(session=session)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token token-admin")

    resp = client.get("/api/v1/fts/audit-logs/?actor_id=1")
    assert resp.status_code == status.HTTP_200_OK

    resp_bad = client.get("/api/v1/fts/audit-logs/?actor_id=invalid")
    assert resp_bad.status_code == status.HTTP_400_BAD_REQUEST


def test_user_search_api(stub_iam):
    from modules.directory.models import UserRef as DirUserRef

    DirUserRef.objects.create(
        user_id=102,
        username="u102",
        display_name="Dr. Rao",
        kind="faculty",
        department="CSE",
        is_active=True,
    )
    DirUserRef.objects.create(
        user_id=103,
        username="u103",
        display_name="Student Bob",
        kind="student",
        is_active=True,
    )

    session = make_session(
        user_id=101,
        kind="faculty",
        permissions=EMPLOYEE_PERMS,
        modules=["fts"],
    )
    stub_iam(session=session)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token token-101")

    resp = client.get("/api/v1/fts/users/search/?q=Rao")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert len(data) == 1
    assert data[0]["user_id"] == 102
