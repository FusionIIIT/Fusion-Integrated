"""API integration tests for File Tracking System."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from conftest import make_session

pytestmark = pytest.mark.django_db


def _client(stub_iam, **kw):
    modules = kw.pop("modules", ("filetracking",))
    stub_iam(make_session(modules=modules, **kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def test_inbox_and_outbox_api(stub_iam):
    client1 = _client(
        stub_iam,
        user_id=1,
        active_role="faculty",
        permissions=("filetracking.file.view", "filetracking.file.create"),
    )

    # Create file circulating to user 2
    res = client1.post(
        "/api/v1/filetracking/files/",
        {
            "subject": "Dean Approval Memo",
            "initial_comment": "Please approve memo",
            "is_draft": False,
            "recipient_user_id": 2,
            "recipient_designation": "Dean Academic",
        },
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED
    file_id = res.json()["id"]

    # User 1 checks outbox
    res_outbox = client1.get("/api/v1/filetracking/files/outbox/")
    assert res_outbox.status_code == status.HTTP_200_OK
    assert any(f["id"] == file_id for f in res_outbox.json())

    # User 2 checks inbox
    client2 = _client(
        stub_iam,
        user_id=2,
        active_role="Dean Academic",
        permissions=("filetracking.file.view", "filetracking.file.forward"),
    )
    res_inbox = client2.get("/api/v1/filetracking/files/inbox/")
    assert res_inbox.status_code == status.HTTP_200_OK
    assert any(f["id"] == file_id for f in res_inbox.json())


def test_unauthorized_user_scoping_yields_404(stub_iam):
    client1 = _client(
        stub_iam,
        user_id=1,
        active_role="faculty",
        permissions=("filetracking.file.create", "filetracking.file.view"),
    )
    res = client1.post(
        "/api/v1/filetracking/files/",
        {
            "subject": "Private File",
            "initial_comment": "Private remark",
            "is_draft": True,
        },
        format="json",
    )
    file_id = res.json()["id"]

    # User 99 (not associated) tries to read detail -> gets 404, never 403 (BR-FTS-009)
    client99 = _client(
        stub_iam,
        user_id=99,
        active_role="staff",
        permissions=("filetracking.file.view",),
    )
    res_detail = client99.get(f"/api/v1/filetracking/files/{file_id}/")
    assert res_detail.status_code == status.HTTP_404_NOT_FOUND


def test_missing_initial_comment_returns_400(stub_iam):
    client = _client(
        stub_iam,
        user_id=1,
        permissions=("filetracking.file.create",),
    )
    res = client.post(
        "/api/v1/filetracking/files/",
        {
            "subject": "Missing Note",
            "initial_comment": "   ",
            "is_draft": True,
        },
        format="json",
    )
    assert res.status_code == status.HTTP_400_BAD_REQUEST
