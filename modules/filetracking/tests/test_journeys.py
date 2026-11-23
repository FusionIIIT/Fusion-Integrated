"""End-to-end journey tests for File Tracking System driving HTTP endpoints (Step 5.12)."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from conftest import make_session
from modules.filetracking.models import (
    FileAuditLog,
    FileStatus,
    TrackedFile,
)

pytestmark = pytest.mark.django_db


def _client(stub_iam, **kw):
    modules = kw.pop("modules", ("filetracking",))
    stub_iam(make_session(modules=modules, **kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token journey-token")
    return c


def test_fts_uc_001_create_and_circulate_file(stub_iam):
    """FTS-UC-001: Create and circulate institutional file directly."""
    creator = _client(
        stub_iam,
        user_id=101,
        active_role="faculty",
        permissions=("filetracking.file.create", "filetracking.file.view"),
    )
    res = creator.post(
        "/api/v1/filetracking/files/",
        {
            "subject": "Equipment Procurement Request",
            "initial_comment": "Please approve budget allocation.",
            "is_draft": False,
            "recipient_user_id": 102,
            "recipient_designation": "HOD CSE",
            "attachments": [
                {
                    "file_name": "quotation.pdf",
                    "file_size": 2048,
                    "mime_type": "application/pdf",
                    "storage_key": "proc/quote.pdf",
                }
            ],
        },
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()
    assert data["status"] == FileStatus.CIRCULATING
    assert data["current_holder_user_id"] == 102
    file_id = data["id"]

    # Verify rows created
    file_obj = TrackedFile.objects.get(id=file_id)
    assert file_obj.status == FileStatus.CIRCULATING
    assert file_obj.attachments.count() == 1
    assert file_obj.movements.count() == 1
    assert FileAuditLog.objects.filter(file_id=file_id).count() >= 1


def test_fts_uc_002_create_and_discard_draft(stub_iam):
    """FTS-UC-002: Create uncirculated draft and discard it."""
    owner = _client(
        stub_iam,
        user_id=103,
        active_role="staff",
        permissions=("filetracking.file.create", "filetracking.file.view"),
    )
    # 1. Create Draft
    res = owner.post(
        "/api/v1/filetracking/files/",
        {
            "subject": "Draft Agenda Notes",
            "initial_comment": "Early thoughts for meeting.",
            "is_draft": True,
        },
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED
    file_id = res.json()["id"]

    # Verify in drafts
    res_drafts = owner.get("/api/v1/filetracking/files/drafts/")
    assert res_drafts.status_code == status.HTTP_200_OK
    assert any(d["id"] == file_id for d in res_drafts.json())

    # 2. Discard Draft
    res_discard = owner.delete(f"/api/v1/filetracking/files/{file_id}/draft/discard/")
    assert res_discard.status_code == status.HTTP_204_NO_CONTENT
    assert not TrackedFile.objects.filter(id=file_id).exists()


def test_fts_uc_003_update_uncirculated_draft(stub_iam):
    """FTS-UC-003: Update metadata and attachments on an uncirculated draft."""
    owner = _client(
        stub_iam,
        user_id=104,
        active_role="faculty",
        permissions=("filetracking.file.create", "filetracking.file.view"),
    )
    res = owner.post(
        "/api/v1/filetracking/files/",
        {
            "subject": "Original Title",
            "initial_comment": "First draft draft note",
            "is_draft": True,
        },
        format="json",
    )
    file_id = res.json()["id"]

    res_put = owner.put(
        f"/api/v1/filetracking/files/{file_id}/draft/",
        {
            "subject": "Updated Title",
            "description": "Updated Description text",
            "attachments": [
                {
                    "file_name": "memo_v2.pdf",
                    "file_size": 1024,
                    "mime_type": "application/pdf",
                    "storage_key": "drafts/memo_v2.pdf",
                }
            ],
        },
        format="json",
    )
    assert res_put.status_code == status.HTTP_200_OK
    data = res_put.json()
    assert data["subject"] == "Updated Title"
    assert data["description"] == "Updated Description text"
    assert len(data["attachments"]) == 1


def test_fts_uc_004_and_005_forward_and_return_file(stub_iam):
    """FTS-UC-004 & FTS-UC-005: Forward to employee, and return to previous sender."""
    s1 = make_session(
        modules=("filetracking",),
        user_id=201,
        active_role="faculty",
        permissions=("filetracking.file.create", "filetracking.file.view", "filetracking.file.forward"),
    )
    s2 = make_session(
        modules=("filetracking",),
        user_id=202,
        active_role="Dean Academic",
        permissions=("filetracking.file.view", "filetracking.file.forward", "filetracking.file.return"),
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token journey-token")

    # User 1 creates and sends to User 2
    stub_iam(s1)
    res_create = client.post(
        "/api/v1/filetracking/files/",
        {
            "subject": "Curriculum Revision Proposal",
            "initial_comment": "Please review changes",
            "is_draft": False,
            "recipient_user_id": 202,
            "recipient_designation": "Dean Academic",
        },
        format="json",
    )
    assert res_create.status_code == status.HTTP_201_CREATED
    file_id = res_create.json()["id"]

    # User 2 returns file back to User 1 (FTS-UC-005)
    stub_iam(s2)
    res_return = client.post(
        f"/api/v1/filetracking/files/{file_id}/return/",
        {"comment": "Please add department committee minutes first."},
        format="json",
    )
    assert res_return.status_code == status.HTTP_200_OK
    mov = res_return.json()
    assert mov["receiver_user_id"] == 201

    # User 1 re-forwards to User 2 (FTS-UC-004)
    stub_iam(s1)
    res_fwd = client.post(
        f"/api/v1/filetracking/files/{file_id}/forward/",
        {
            "recipient_user_id": 202,
            "recipient_designation": "Dean Academic",
            "comment": "Minutes attached as requested.",
        },
        format="json",
    )
    assert res_fwd.status_code == status.HTTP_200_OK
    assert res_fwd.json()["receiver_user_id"] == 202


def test_fts_uc_006_view_movement_history(stub_iam):
    """FTS-UC-006: View file movement history."""
    user1 = _client(
        stub_iam,
        user_id=301,
        permissions=("filetracking.file.create", "filetracking.file.view"),
    )
    res = user1.post(
        "/api/v1/filetracking/files/",
        {
            "subject": "Lab Safety Audit",
            "initial_comment": "Initial submission",
            "is_draft": False,
            "recipient_user_id": 302,
        },
        format="json",
    )
    file_id = res.json()["id"]

    res_history = user1.get(f"/api/v1/filetracking/files/{file_id}/history/")
    assert res_history.status_code == status.HTTP_200_OK
    movements = res_history.json()
    assert len(movements) == 1
    assert movements[0]["sender_user_id"] == 301


def test_fts_uc_007_archive_file(stub_iam):
    """FTS-UC-007: Owner archives completed circulated file."""
    owner = _client(
        stub_iam,
        user_id=401,
        permissions=(
            "filetracking.file.create",
            "filetracking.file.view",
            "filetracking.file.forward",
            "filetracking.file.archive",
        ),
    )
    res = owner.post(
        "/api/v1/filetracking/files/",
        {
            "subject": "Conference Sponsorship",
            "initial_comment": "Submitted for approval",
            "is_draft": False,
            "recipient_user_id": 402,
        },
        format="json",
    )
    file_id = res.json()["id"]

    res_archive = owner.post(
        f"/api/v1/filetracking/files/{file_id}/archive/",
        {"comment": "Conference completed and settlement done."},
        format="json",
    )
    assert res_archive.status_code == status.HTTP_200_OK
    assert res_archive.json()["status"] == FileStatus.ARCHIVED


def test_fts_uc_008_009_010_view_views(stub_iam):
    """FTS-UC-008, 009, 010: List inbox, outbox, and archived views."""
    user = _client(
        stub_iam,
        user_id=501,
        permissions=("filetracking.file.create", "filetracking.file.view", "filetracking.file.archive"),
    )
    # Create draft
    user.post(
        "/api/v1/filetracking/files/",
        {"subject": "Draft F1", "initial_comment": "Draft note", "is_draft": True},
        format="json",
    )
    # Create circulating
    res_circ = user.post(
        "/api/v1/filetracking/files/",
        {"subject": "Circ F2", "initial_comment": "Sent note", "is_draft": False, "recipient_user_id": 502},
        format="json",
    )
    f2_id = res_circ.json()["id"]

    # Archive f2
    user.post(f"/api/v1/filetracking/files/{f2_id}/archive/", {"comment": "Done"}, format="json")

    # Check views
    assert user.get("/api/v1/filetracking/files/inbox/").status_code == status.HTTP_200_OK
    assert user.get("/api/v1/filetracking/files/outbox/").status_code == status.HTTP_200_OK
    assert user.get("/api/v1/filetracking/files/archived/").status_code == status.HTTP_200_OK
    assert user.get("/api/v1/filetracking/files/drafts/").status_code == status.HTTP_200_OK
