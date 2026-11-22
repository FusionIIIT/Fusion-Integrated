"""Specification tests for Requirements Registry (FR) strategy - Part 1.

Generated from frozen FR_DESIGN.json.
Coverage: AFR-FTS-001 through AFR-FTS-041 (TC-FTS-001 through TC-FTS-045).
"""
from __future__ import annotations

import pytest
from rest_framework import status

from modules.fts.domain.state_machine import (
    STATE_ARCHIVED,
    STATE_CIRCULATED,
    STATE_DISCARDED,
    STATE_DRAFT,
)
from modules.fts.models.audit import FileAuditLog
from modules.fts.models.files import File
from modules.fts.services.files import create_file

pytestmark = pytest.mark.django_db


def test_tc_fts_001(fts_client):
    """TC-FTS-001 [AFR-FTS-001].

    Verify that a file is treated as a persistent composite object containing
    mandatory comments and optional file attachments.
    """
    res = fts_client(user_id=101, kind="faculty", active_role="Assistant Professor").post(
        "/api/v1/fts/files/",
        data={
            "subject": "FR-001 Composite File",
            "comment": "Mandatory initial comment.",
            "is_draft": True,
            "attachments": [
                {
                    "file_name": "spec.pdf",
                    "file_url": "https://storage.fusion.ac.in/fts/spec.pdf",
                    "file_size": 1024,
                    "mime_type": "application/pdf",
                }
            ],
        },
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()
    assert len(data["comments"]) == 1
    assert data["comments"][0]["comment_text"] == "Mandatory initial comment."
    assert len(data["attachments"]) == 1
    assert data["attachments"][0]["file_name"] == "spec.pdf"


def test_tc_fts_002(fts_client):
    """TC-FTS-002 [AFR-FTS-002].

    Verify that a circulated file and its accumulated contents cannot be deleted.
    """
    f = create_file(
        subject="FR-002 No Delete",
        comment_text="Initial remark.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Staff",
    )
    res = fts_client(user_id=101).post(f"/api/v1/fts/files/{f.id}/discard/")
    assert res.status_code == status.HTTP_409_CONFLICT
    f.refresh_from_db()
    assert f.status == STATE_CIRCULATED


def test_tc_fts_003(fts_client):
    """TC-FTS-003 [AFR-FTS-003].

    Verify that the file owner can archive a completed file instead of deleting it.
    """
    f = create_file(
        subject="FR-003 Archive File",
        comment_text="Initial remark.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Staff",
    )
    res = fts_client(user_id=101).post(f"/api/v1/fts/files/{f.id}/archive/")
    assert res.status_code == status.HTTP_200_OK
    f.refresh_from_db()
    assert f.status == STATE_ARCHIVED
    assert File.objects.filter(id=f.id).exists()


def test_tc_fts_004(fts_client):
    """TC-FTS-004 [AFR-FTS-004].

    Verify that FTS maintains traceability for file creation, movement, comments, attachments, and archival.
    """
    f = create_file(
        subject="FR-004 Traceability",
        comment_text="Creation trace.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="faculty_101",
        recipient_role="Assistant Professor",
    )
    fts_client(user_id=101).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={"to_user_id": 202, "to_username": "staff_202", "to_role": "Staff", "comment": "Movement trace."},
        format="json",
    )
    fts_client(user_id=101).post(f"/api/v1/fts/files/{f.id}/archive/")

    logs = FileAuditLog.objects.filter(file_id=f.id).values_list("action", flat=True)
    assert "FILE_CREATED" in logs
    assert "FILE_FORWARDED" in logs
    assert "FILE_ARCHIVED" in logs


def test_tc_fts_005(fts_client):
    """TC-FTS-005 [AFR-FTS-005].

    Verify that Institute Employees (Faculty and Staff) are supported as operational users.
    """
    res_fac = fts_client(user_id=101, kind="faculty", active_role="Professor").post(
        "/api/v1/fts/files/",
        data={"subject": "Faculty Operational", "comment": "Comment.", "is_draft": True},
        format="json",
    )
    assert res_fac.status_code == status.HTTP_201_CREATED

    res_staff = fts_client(user_id=202, kind="staff", active_role="Superintendent").post(
        "/api/v1/fts/files/",
        data={"subject": "Staff Operational", "comment": "Comment.", "is_draft": True},
        format="json",
    )
    assert res_staff.status_code == status.HTTP_201_CREATED


def test_tc_fts_006(admin_client):
    """TC-FTS-006 [AFR-FTS-006].

    Verify that System Admin can view governance access context and audit logs.
    """
    res = admin_client().get("/api/v1/fts/governance/audit-logs/")
    assert res.status_code == status.HTTP_200_OK


def test_tc_fts_007(admin_client):
    """TC-FTS-007 [AFR-FTS-007].

    Verify that System Admin can monitor FTS system usage.
    """
    res = admin_client().get("/api/v1/fts/governance/usage/")
    assert res.status_code == status.HTTP_200_OK
    assert "total_files" in res.json()


def test_tc_fts_008(admin_client):
    """TC-FTS-008 [AFR-FTS-008].

    Verify that System Admin can view FTS security and audit logs.
    """
    res = admin_client().get("/api/v1/fts/governance/audit-logs/")
    assert res.status_code == status.HTTP_200_OK
    assert isinstance(res.json(), list)


def test_tc_fts_009(admin_client):
    """TC-FTS-009 [AFR-FTS-009].

    Verify that System Admin cannot perform operational file workflow actions.
    """
    c = admin_client()
    res = c.post(
        "/api/v1/fts/files/",
        data={"subject": "Admin Operation Attempt", "comment": "Comment."},
        format="json",
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_tc_fts_010(fts_client):
    """TC-FTS-010 [AFR-FTS-010].

    Verify that an Institute Employee assigned multiple roles can operate under selected role.
    """
    res = fts_client(user_id=101, active_role="HOD (CSE)").post(
        "/api/v1/fts/files/",
        data={"subject": "Role Switch File", "comment": "Comment.", "is_draft": True},
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED
    assert res.json()["owner_role"] == "HOD (CSE)"


def test_tc_fts_011(fts_client):
    """TC-FTS-011 [AFR-FTS-011].

    Verify that any authorized Institute Employee can create a new file under an assigned role.
    """
    res = fts_client(user_id=101, active_role="Assistant Professor").post(
        "/api/v1/fts/files/",
        data={"subject": "Authorized Create", "comment": "Initial comment.", "is_draft": True},
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED


def test_tc_fts_012(fts_client):
    """TC-FTS-012 [AFR-FTS-012 — mandatory comment required].

    Verify that file creation requires a mandatory initial comment.
    """
    res = fts_client(user_id=101).post(
        "/api/v1/fts/files/",
        data={"subject": "Missing Comment", "comment": "", "is_draft": True},
        format="json",
    )
    assert res.status_code == status.HTTP_400_BAD_REQUEST


def test_tc_fts_013(fts_client):
    """TC-FTS-013 [AFR-FTS-012 — mandatory comment accepted].

    Verify that file creation succeeds when a mandatory initial comment is provided.
    """
    res = fts_client(user_id=101).post(
        "/api/v1/fts/files/",
        data={"subject": "Accepted Comment File", "comment": "Non-empty mandatory comment.", "is_draft": True},
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED


def test_tc_fts_014(fts_client):
    """TC-FTS-014 [AFR-FTS-013].

    Verify that optional attachments can be added during file creation.
    """
    res = fts_client(user_id=101).post(
        "/api/v1/fts/files/",
        data={
            "subject": "Attached File",
            "comment": "Comment.",
            "is_draft": True,
            "attachments": [
                {
                    "file_name": "data.csv",
                    "file_url": "https://storage.fusion.ac.in/fts/data.csv",
                    "file_size": 512,
                    "mime_type": "text/csv",
                }
            ],
        },
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED
    assert len(res.json()["attachments"]) == 1


def test_tc_fts_015(fts_client):
    """TC-FTS-015 [AFR-FTS-014].

    Verify that an Institute Employee can save a newly created file as a draft.
    """
    res = fts_client(user_id=101).post(
        "/api/v1/fts/files/",
        data={"subject": "Draft File", "comment": "Comment.", "is_draft": True},
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED
    assert res.json()["status"] == STATE_DRAFT


def test_tc_fts_016(fts_client):
    """TC-FTS-016 [AFR-FTS-015].

    Verify that a saved draft file can be edited before submission.
    """
    f = create_file(
        subject="Pre-edit Draft",
        comment_text="Original.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=True,
    )
    res = fts_client(user_id=101).put(
        f"/api/v1/fts/files/{f.id}/",
        data={"subject": "Post-edit Draft", "comment": "Updated."},
        format="json",
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["subject"] == "Post-edit Draft"


def test_tc_fts_017(fts_client):
    """TC-FTS-017 [AFR-FTS-016].

    Verify that a draft file can be discarded before submission.
    """
    f = create_file(
        subject="Draft Discard",
        comment_text="Original.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=True,
    )
    res = fts_client(user_id=101).post(f"/api/v1/fts/files/{f.id}/discard/")
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["status"] == STATE_DISCARDED


def test_tc_fts_018(fts_client):
    """TC-FTS-018 [AFR-FTS-017].

    Verify that a circulated file cannot be deleted.
    """
    f = create_file(
        subject="Circulated No Discard",
        comment_text="Original.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Staff",
    )
    res = fts_client(user_id=101).post(f"/api/v1/fts/files/{f.id}/discard/")
    assert res.status_code == status.HTTP_409_CONFLICT


def test_tc_fts_019(fts_client):
    """TC-FTS-019 [AFR-FTS-018].

    Verify that file state transitions from draft to circulated upon submission.
    """
    f = create_file(
        subject="Transition to Circulate",
        comment_text="Draft comment.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=True,
    )
    res = fts_client(user_id=101).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={"to_user_id": 202, "to_username": "staff_202", "to_role": "Staff", "comment": "First forward."},
        format="json",
    )
    assert res.status_code == status.HTTP_200_OK
    f.refresh_from_db()
    assert f.status == STATE_CIRCULATED


def test_tc_fts_020(fts_client):
    """TC-FTS-020 [AFR-FTS-019].

    Verify that comments and attachments accumulated in a file are preserved after submission.
    """
    f = create_file(
        subject="Preserve Accumulated Content",
        comment_text="Draft initial remark.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=True,
        attachments=[
            {
                "file_name": "draft_doc.pdf",
                "file_url": "https://storage.fusion.ac.in/fts/draft_doc.pdf",
                "file_size": 2048,
                "mime_type": "application/pdf",
            }
        ],
    )
    fts_client(user_id=101).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={"to_user_id": 202, "to_username": "staff_202", "to_role": "Staff", "comment": "Forwarding."},
        format="json",
    )
    detail = fts_client(user_id=101).get(f"/api/v1/fts/files/{f.id}/").json()
    assert any(c["comment_text"] == "Draft initial remark." for c in detail["comments"])
    assert any(a["file_name"] == "draft_doc.pdf" for a in detail["attachments"])


def test_tc_fts_021(fts_client):
    """TC-FTS-021 [AFR-FTS-020].

    Verify that an Institute Employee can send a file to another Institute Employee.
    """
    f = create_file(
        subject="Send Employee File",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="faculty_101",
        recipient_role="Professor",
    )
    res = fts_client(user_id=101).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={"to_user_id": 202, "to_username": "staff_202", "to_role": "Staff", "comment": "Sending to 202."},
        format="json",
    )
    assert res.status_code == status.HTTP_200_OK


def test_tc_fts_022(fts_client):
    """TC-FTS-022 [AFR-FTS-021].

    Verify that a file can be sent to any Institute Employee regardless of receiver role.
    """
    f = create_file(
        subject="Any Role File",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="faculty_101",
        recipient_role="Professor",
    )
    # Forward to any role (e.g. Lab Technician, Librarian)
    res = fts_client(user_id=101).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={"to_user_id": 404, "to_username": "tech_404", "to_role": "Lab Technician", "comment": "To Lab Tech."},
        format="json",
    )
    assert res.status_code == status.HTTP_200_OK


def test_tc_fts_023(fts_client):
    """TC-FTS-023 [AFR-FTS-022 — mandatory comment required at movement].

    Verify that a mandatory comment is required for every file-movement action (forward).
    """
    f = create_file(
        subject="Movement Comment Guard",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="faculty_101",
        recipient_role="Professor",
    )
    res = fts_client(user_id=101).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={"to_user_id": 202, "to_username": "staff_202", "to_role": "Staff", "comment": "   "},
        format="json",
    )
    assert res.status_code == status.HTTP_400_BAD_REQUEST


def test_tc_fts_024(fts_client):
    """TC-FTS-024 [AFR-FTS-022 — mandatory comment required at return].

    Verify that a mandatory comment is required for every file-movement action (return).
    """
    f = create_file(
        subject="Return Comment Guard",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Staff",
    )
    res = fts_client(user_id=202).post(
        f"/api/v1/fts/files/{f.id}/return/",
        data={"comment": ""},
        format="json",
    )
    assert res.status_code == status.HTTP_400_BAD_REQUEST


def test_tc_fts_025(fts_client):
    """TC-FTS-025 [AFR-FTS-023].

    Verify that optional attachments can be added at a forwarding movement stage.
    """
    f = create_file(
        subject="Forward Attachment Stage",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="faculty_101",
        recipient_role="Professor",
    )
    res = fts_client(user_id=101).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={
            "to_user_id": 202,
            "to_username": "staff_202",
            "to_role": "Staff",
            "comment": "Adding bill.",
            "attachments": [
                {
                    "file_name": "bill.pdf",
                    "file_url": "https://storage.fusion.ac.in/fts/bill.pdf",
                    "file_size": 3000,
                    "mime_type": "application/pdf",
                }
            ],
        },
        format="json",
    )
    assert res.status_code == status.HTTP_200_OK


def test_tc_fts_026(fts_client):
    """TC-FTS-026 [AFR-FTS-023 — optional attachment at return stage].

    Verify that optional attachments can be added at a return movement stage.
    """
    f = create_file(
        subject="Return Attachment Stage",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Staff",
    )
    res = fts_client(user_id=202).post(
        f"/api/v1/fts/files/{f.id}/return/",
        data={
            "comment": "Returning with rejection slip.",
            "attachments": [
                {
                    "file_name": "slip.pdf",
                    "file_url": "https://storage.fusion.ac.in/fts/slip.pdf",
                    "file_size": 2500,
                    "mime_type": "application/pdf",
                }
            ],
        },
        format="json",
    )
    assert res.status_code == status.HTTP_200_OK


def test_tc_fts_027(fts_client):
    """TC-FTS-027 [AFR-FTS-024].

    Verify that a recipient user can forward a received file to another user.
    """
    f = create_file(
        subject="Recipient Forwarding Onward",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Staff",
    )
    res = fts_client(user_id=202).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={"to_user_id": 303, "to_username": "dean_303", "to_role": "Dean", "comment": "Forwarding onward."},
        format="json",
    )
    assert res.status_code == status.HTTP_200_OK
    f.refresh_from_db()
    assert f.current_holder_user_id == 303


def test_tc_fts_028(fts_client):
    """TC-FTS-028 [AFR-FTS-025].

    Verify that a recipient user can return a received file to the sender.
    """
    f = create_file(
        subject="Recipient Return File",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Staff",
    )
    res = fts_client(user_id=202).post(
        f"/api/v1/fts/files/{f.id}/return/",
        data={"comment": "Returning file."},
        format="json",
    )
    assert res.status_code == status.HTTP_200_OK
    f.refresh_from_db()
    assert f.current_holder_user_id == 101


def test_tc_fts_029(fts_client):
    """TC-FTS-029 [AFR-FTS-026].

    Verify that each forwarding action is recorded in chronological order.
    """
    f = create_file(
        subject="Chronological Order Forward",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="faculty_101",
        recipient_role="Professor",
    )
    fts_client(user_id=101).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={"to_user_id": 202, "to_username": "staff_202", "to_role": "Staff", "comment": "Action 1."},
        format="json",
    )
    fts_client(user_id=202).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={"to_user_id": 303, "to_username": "dean_303", "to_role": "Dean", "comment": "Action 2."},
        format="json",
    )
    history = fts_client(user_id=101).get(f"/api/v1/fts/files/{f.id}/history/").json()
    sequences = [m["sequence"] for m in history]
    assert sequences == sorted(sequences)


def test_tc_fts_030(fts_client):
    """TC-FTS-030 [AFR-FTS-027].

    Verify that each return action is recorded in chronological order.
    """
    f = create_file(
        subject="Chronological Order Return",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Staff",
    )
    fts_client(user_id=202).post(
        f"/api/v1/fts/files/{f.id}/return/",
        data={"comment": "Return action."},
        format="json",
    )
    history = fts_client(user_id=101).get(f"/api/v1/fts/files/{f.id}/history/").json()
    assert history[-1]["movement_type"] == "RETURN"
    assert history[-1]["sequence"] == 2


def test_tc_fts_031(fts_client):
    """TC-FTS-031 [AFR-FTS-028].

    Verify that the current file holder is updated after a forwarding action.
    """
    f = create_file(
        subject="Holder Update Forward",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="faculty_101",
        recipient_role="Professor",
    )
    fts_client(user_id=101).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={"to_user_id": 202, "to_username": "staff_202", "to_role": "Staff", "comment": "Fwd."},
        format="json",
    )
    f.refresh_from_db()
    assert f.current_holder_user_id == 202


def test_tc_fts_032(fts_client):
    """TC-FTS-032 [AFR-FTS-028 — holder update on return].

    Verify that the current file holder is updated after a return action.
    """
    f = create_file(
        subject="Holder Update Return",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Staff",
    )
    fts_client(user_id=202).post(
        f"/api/v1/fts/files/{f.id}/return/",
        data={"comment": "Return."},
        format="json",
    )
    f.refresh_from_db()
    assert f.current_holder_user_id == 101


def test_tc_fts_033(fts_client):
    """TC-FTS-033 [AFR-FTS-029].

    Verify that files received by a user appear in the user's Inbox.
    """
    f = create_file(
        subject="Inbox Appear File",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Staff",
    )
    inbox = fts_client(user_id=202).get("/api/v1/fts/inbox/").json()
    assert any(item["id"] == f.id for item in inbox)


def test_tc_fts_034(fts_client):
    """TC-FTS-034 [AFR-FTS-030].

    Verify that files sent by a user appear in the user's Outbox.
    """
    f = create_file(
        subject="Outbox Appear File",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Staff",
    )
    outbox = fts_client(user_id=101).get("/api/v1/fts/outbox/").json()
    assert any(item["id"] == f.id for item in outbox)


def test_tc_fts_035(fts_client):
    """TC-FTS-035 [AFR-FTS-031].

    Verify that users can view and open files from their Inbox.
    """
    f = create_file(
        subject="Open From Inbox",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Staff",
    )
    res = fts_client(user_id=202).get(f"/api/v1/fts/files/{f.id}/")
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["id"] == f.id


def test_tc_fts_036(fts_client):
    """TC-FTS-036 [AFR-FTS-032].

    Verify that users can view and open files from their Outbox.
    """
    f = create_file(
        subject="Open From Outbox",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Staff",
    )
    res = fts_client(user_id=101).get(f"/api/v1/fts/files/{f.id}/")
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["id"] == f.id


def test_tc_fts_037(fts_client):
    """TC-FTS-037 [AFR-FTS-033].

    Verify that a user can act on an actionable file from Inbox according to file state and authorization.
    """
    f = create_file(
        subject="Actionable Inbox File",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Staff",
    )
    res = fts_client(user_id=202).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={"to_user_id": 303, "to_username": "dean", "to_role": "Dean", "comment": "Acting from inbox."},
        format="json",
    )
    assert res.status_code == status.HTTP_200_OK


def test_tc_fts_038(fts_client):
    """TC-FTS-038 [AFR-FTS-034].

    Verify that files remain accessible to associated users until the file owner archives the file.
    """
    f = create_file(
        subject="Accessible Pre-archive",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Staff",
    )
    assert fts_client(user_id=101).get(f"/api/v1/fts/files/{f.id}/").status_code == status.HTTP_200_OK
    assert fts_client(user_id=202).get(f"/api/v1/fts/files/{f.id}/").status_code == status.HTTP_200_OK


def test_tc_fts_039(fts_client):
    """TC-FTS-039 [AFR-FTS-035].

    Verify that complete movement history is maintained for every file from creation onward.
    """
    f = create_file(
        subject="Complete History",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="faculty_101",
        recipient_role="Professor",
    )
    fts_client(user_id=101).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={"to_user_id": 202, "to_username": "staff_202", "to_role": "Staff", "comment": "Fwd."},
        format="json",
    )
    history = fts_client(user_id=101).get(f"/api/v1/fts/files/{f.id}/history/").json()
    assert len(history) == 2


def test_tc_fts_040(fts_client):
    """TC-FTS-040 [AFR-FTS-036].

    Verify that sender details are recorded for each file movement event.
    """
    f = create_file(
        subject="Sender Details",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Staff",
    )
    history = fts_client(user_id=101).get(f"/api/v1/fts/files/{f.id}/history/").json()
    assert history[0]["from_user_id"] == 101
    assert history[0]["from_username"] == "faculty_101"


def test_tc_fts_041(fts_client):
    """TC-FTS-041 [AFR-FTS-037].

    Verify that receiver details are recorded for each file movement event.
    """
    f = create_file(
        subject="Receiver Details",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Staff",
    )
    history = fts_client(user_id=101).get(f"/api/v1/fts/files/{f.id}/history/").json()
    assert history[0]["to_user_id"] == 202
    assert history[0]["to_username"] == "staff_202"


def test_tc_fts_042(fts_client):
    """TC-FTS-042 [AFR-FTS-038].

    Verify that timestamps are recorded for each file movement event.
    """
    f = create_file(
        subject="Timestamp Recorded",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Staff",
    )
    history = fts_client(user_id=101).get(f"/api/v1/fts/files/{f.id}/history/").json()
    assert "created_at" in history[0] or "timestamp" in history[0]


def test_tc_fts_043(fts_client):
    """TC-FTS-043 [AFR-FTS-039].

    Verify that comments added at each file movement event are recorded in the movement history.
    """
    f = create_file(
        subject="Movement Comment Recorded",
        comment_text="Review section 2.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Staff",
    )
    history = fts_client(user_id=101).get(f"/api/v1/fts/files/{f.id}/history/").json()
    assert any(c["comment_text"] == "Review section 2." for c in history[0]["comments"])


def test_tc_fts_044(fts_client):
    """TC-FTS-044 [AFR-FTS-040].

    Verify that attachments added at each file movement event are recorded in the movement history.
    """
    f = create_file(
        subject="Movement Attachment Recorded",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Staff",
        attachments=[
            {
                "file_name": "report.pdf",
                "file_url": "https://storage.fusion.ac.in/fts/report.pdf",
                "file_size": 4096,
                "mime_type": "application/pdf",
            }
        ],
    )
    history = fts_client(user_id=101).get(f"/api/v1/fts/files/{f.id}/history/").json()
    assert any(a["file_name"] == "report.pdf" for a in history[0]["attachments"])


def test_tc_fts_045(fts_client):
    """TC-FTS-045 [AFR-FTS-041].

    Verify that any user associated with a file can view that file's tracking history.
    """
    f = create_file(
        subject="Tracking History Access",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Staff",
    )
    res = fts_client(user_id=202).get(f"/api/v1/fts/files/{f.id}/history/")
    assert res.status_code == status.HTTP_200_OK
    assert len(res.json()) >= 1
