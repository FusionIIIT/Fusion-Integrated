"""Adversarial and malicious insider tests for File Tracking System (Step 5.11)."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from conftest import make_session

pytestmark = pytest.mark.django_db


def _client(stub_iam, **kw):
    modules = kw.pop("modules", ("filetracking",))
    stub_iam(make_session(modules=modules, **kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token adv-token")
    return c


def test_adversarial_non_associated_user_gets_404(stub_iam):
    """Can someone act on or view a file outside their scope? Yields 404 (BR-FTS-009)."""
    user1 = _client(stub_iam, user_id=1, permissions=("filetracking.file.create", "filetracking.file.view"))
    res = user1.post(
        "/api/v1/filetracking/files/",
        {"subject": "Confidential Appraisal", "initial_comment": "Private", "is_draft": True},
        format="json",
    )
    file_id = res.json()["id"]

    outsider = _client(stub_iam, user_id=999, permissions=("filetracking.file.view",))
    res_get = outsider.get(f"/api/v1/filetracking/files/{file_id}/")
    assert res_get.status_code == status.HTTP_404_NOT_FOUND

    res_history = outsider.get(f"/api/v1/filetracking/files/{file_id}/history/")
    assert res_history.status_code == status.HTTP_404_NOT_FOUND


def test_adversarial_non_holder_cannot_forward(stub_iam):
    """Can a user who is not the current holder forward a circulated file? (BR-FTS-003)."""
    creator = _client(
        stub_iam,
        user_id=10,
        permissions=("filetracking.file.create", "filetracking.file.view", "filetracking.file.forward"),
    )
    res = creator.post(
        "/api/v1/filetracking/files/",
        {
            "subject": "Inter-department memo",
            "initial_comment": "Please advise",
            "is_draft": False,
            "recipient_user_id": 20,
        },
        format="json",
    )
    file_id = res.json()["id"]

    # Creator (user 10) is no longer the current holder (user 20 is)
    res_fwd = creator.post(
        f"/api/v1/filetracking/files/{file_id}/forward/",
        {"recipient_user_id": 30, "comment": "Trying to forward without holding"},
        format="json",
    )
    assert res_fwd.status_code == status.HTTP_403_FORBIDDEN


def test_adversarial_cannot_forward_to_self(stub_iam):
    """Can someone forward a file to themselves? Refused with 400 (BR-FTS-002)."""
    user = _client(
        stub_iam,
        user_id=15,
        permissions=("filetracking.file.create", "filetracking.file.forward"),
    )
    res = user.post(
        "/api/v1/filetracking/files/",
        {
            "subject": "Self send test",
            "initial_comment": "Initial note",
            "is_draft": False,
            "recipient_user_id": 15,
        },
        format="json",
    )
    assert res.status_code == status.HTTP_400_BAD_REQUEST


def test_adversarial_cannot_modify_archived_file(stub_iam):
    """Can an archived record still be changed or forwarded? (BR-FTS-004)."""
    user = _client(
        stub_iam,
        user_id=40,
        permissions=(
            "filetracking.file.create",
            "filetracking.file.view",
            "filetracking.file.forward",
            "filetracking.file.archive",
        ),
    )
    res = user.post(
        "/api/v1/filetracking/files/",
        {
            "subject": "Completed Project",
            "initial_comment": "Wrapping up",
            "is_draft": False,
            "recipient_user_id": 41,
        },
        format="json",
    )
    file_id = res.json()["id"]

    # Archive it
    user.post(f"/api/v1/filetracking/files/{file_id}/archive/", {"comment": "Archiving"}, format="json")

    # Attempt to forward archived file
    res_fwd = user.post(
        f"/api/v1/filetracking/files/{file_id}/forward/",
        {"recipient_user_id": 42, "comment": "Trying to forward archived file"},
        format="json",
    )
    assert res_fwd.status_code == status.HTTP_409_CONFLICT


def test_adversarial_cannot_discard_circulated_file(stub_iam):
    """Can a circulated file be discarded? Refused with 409 Conflict (BR-FTS-005)."""
    user = _client(
        stub_iam,
        user_id=50,
        permissions=("filetracking.file.create", "filetracking.file.view"),
    )
    res = user.post(
        "/api/v1/filetracking/files/",
        {
            "subject": "Official Notice",
            "initial_comment": "Notice sent",
            "is_draft": False,
            "recipient_user_id": 51,
        },
        format="json",
    )
    file_id = res.json()["id"]

    res_discard = user.delete(f"/api/v1/filetracking/files/{file_id}/draft/discard/")
    assert res_discard.status_code == status.HTTP_409_CONFLICT


def test_adversarial_malformed_query_param_gives_400_never_500(stub_iam):
    """Query parameters are hostile input: unparseable ?file_id=abc is 400 never 500."""
    admin = _client(
        stub_iam,
        user_id=99,
        permissions=("filetracking.governance.view",),
    )
    res = admin.get("/api/v1/filetracking/governance/audit/?file_id=not-an-int")
    assert res.status_code == status.HTTP_400_BAD_REQUEST
