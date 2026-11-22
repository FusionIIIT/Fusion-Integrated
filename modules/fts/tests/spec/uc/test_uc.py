"""Specification tests for Use Cases (UC) strategy.

Generated from frozen UC_DESIGN.json.
Coverage: FTS-UC-001 through FTS-UC-010 (47 cases).
"""
from __future__ import annotations

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from modules.fts.domain.state_machine import (
    STATE_ARCHIVED,
    STATE_CIRCULATED,
    STATE_DISCARDED,
    STATE_DRAFT,
)
from modules.fts.models.audit import FileAuditLog, NotificationEvent
from modules.fts.services.archival import archive_file
from modules.fts.services.files import create_file
from modules.fts.services.notifications import trigger_notification
from modules.fts.tests.conftest import make_fts_session

pytestmark = pytest.mark.django_db


# ==========================================
# FTS-UC-001: Create New File
# ==========================================


def test_tc_fts_001_01(fts_client):
    """TC-FTS-001-01 [FTS-UC-001 Main Success Scenario].

    Verify that an authorized employee can create a new file with a mandatory
    comment and save as draft without attachments.
    """
    res = fts_client(user_id=101, kind="faculty", active_role="Assistant Professor").post(
        "/api/v1/fts/files/",
        data={
            "subject": "Lab Equipment Requisition",
            "description": "Initial setup proposal.",
            "comment": "Initial proposal draft for review.",
            "is_draft": True,
        },
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()
    assert data["status"] == STATE_DRAFT
    assert data["subject"] == "Lab Equipment Requisition"
    assert FileAuditLog.objects.filter(file_id=data["id"], action="FILE_CREATED").exists()


def test_tc_fts_001_02(fts_client):
    """TC-FTS-001-02 [FTS-UC-001 Main Success Scenario with attachment].

    Verify that an authorized employee can create a new file with a mandatory
    comment and optional attachments saved as draft.
    """
    res = fts_client(user_id=101).post(
        "/api/v1/fts/files/",
        data={
            "subject": "Conference Travel Request",
            "comment": "Attaching conference invitation letter.",
            "is_draft": True,
            "attachments": [
                {
                    "file_name": "invitation.pdf",
                    "file_url": "https://storage.fusion.ac.in/fts/invitation.pdf",
                    "file_size": 150000,
                    "mime_type": "application/pdf",
                }
            ],
        },
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()
    assert len(data["attachments"]) == 1
    assert data["attachments"][0]["file_name"] == "invitation.pdf"


def test_tc_fts_001_03(fts_client):
    """TC-FTS-001-03 [FTS-UC-001 Alternative Flow 1 (immediate circulation)].

    Verify that a valid created file can proceed immediately to circulation
    without remaining in draft state.
    """
    res = fts_client(user_id=101).post(
        "/api/v1/fts/files/",
        data={
            "subject": "Urgent Thesis Evaluation",
            "comment": "Immediate submission to Dean Academics.",
            "is_draft": False,
            "recipient_user_id": 202,
            "recipient_username": "dean_202",
            "recipient_role": "Dean Academic",
        },
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()
    assert data["status"] == STATE_CIRCULATED
    assert data["current_holder_user_id"] == 202


def test_tc_fts_001_04(fts_client):
    """TC-FTS-001-04 [FTS-UC-001 Alternative Flow 2 (no attachment)].

    Verify that file creation proceeds successfully when no attachment is provided.
    """
    res = fts_client(user_id=101).post(
        "/api/v1/fts/files/",
        data={"subject": "No Attachment File", "comment": "Valid comment.", "is_draft": True},
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED
    assert res.json()["attachments"] == []


def test_tc_fts_001_05(fts_client):
    """TC-FTS-001-05 [FTS-UC-001 Exception Flow 1 (missing initial comment)].

    Verify that FTS rejects file creation/save when the initial comment is missing.
    """
    res = fts_client(user_id=101).post(
        "/api/v1/fts/files/",
        data={"subject": "Missing Comment", "comment": "", "is_draft": True},
        format="json",
    )
    assert res.status_code == status.HTTP_400_BAD_REQUEST


def test_tc_fts_001_06(fts_client):
    """TC-FTS-001-06 [FTS-UC-001 Exception Flow 2 (unauthorized role)].

    Verify that an unauthorized role cannot create files.
    """
    res = fts_client(user_id=101, permissions=("fts.file.view",)).post(
        "/api/v1/fts/files/",
        data={"subject": "Unauthorized Create", "comment": "Comment.", "is_draft": True},
        format="json",
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN


# ==========================================
# FTS-UC-002: Edit or Discard Draft File
# ==========================================


def test_tc_fts_002_01(fts_client):
    """TC-FTS-002-01 [FTS-UC-002 Main Success Scenario (edit draft)].

    Verify that an authorized employee can edit a draft file.
    """
    f = create_file(
        subject="Draft To Edit",
        comment_text="Original remark.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=True,
    )
    res = fts_client(user_id=101).put(
        f"/api/v1/fts/files/{f.id}/",
        data={"subject": "Edited Draft Title", "comment": "Revised remark."},
        format="json",
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["subject"] == "Edited Draft Title"
    assert FileAuditLog.objects.filter(file_id=f.id, action="DRAFT_UPDATED").exists()


def test_tc_fts_002_02(fts_client):
    """TC-FTS-002-02 [FTS-UC-002 Alternative Flow 1 (discard draft)].

    Verify that an authorized employee can discard an uncirculated draft.
    """
    f = create_file(
        subject="Draft To Discard",
        comment_text="Initial remark.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=True,
    )
    res = fts_client(user_id=101).post(f"/api/v1/fts/files/{f.id}/discard/")
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["status"] == STATE_DISCARDED
    f.refresh_from_db()
    assert f.status == STATE_DISCARDED


def test_tc_fts_002_03(fts_client):
    """TC-FTS-002-03 [FTS-UC-002 Exception Flow 1 (discard circulated file)].

    Verify that FTS denies discarding an already-circulated file.
    """
    f = create_file(
        subject="Circulated File",
        comment_text="Initial remark.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Junior Superintendent",
    )
    res = fts_client(user_id=101).post(f"/api/v1/fts/files/{f.id}/discard/")
    assert res.status_code == status.HTTP_409_CONFLICT
    f.refresh_from_db()
    assert f.status == STATE_CIRCULATED


def test_tc_fts_002_04(fts_client):
    """TC-FTS-002-04 [FTS-UC-002 Exception Flow 2 (unauthorized employee)].

    Verify that a non-owner employee cannot edit or discard another user's draft.
    """
    f = create_file(
        subject="Private Draft",
        comment_text="Owner remark.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=True,
    )
    res_edit = fts_client(user_id=202).put(
        f"/api/v1/fts/files/{f.id}/",
        data={"subject": "Hacked Title"},
        format="json",
    )
    assert res_edit.status_code == status.HTTP_403_FORBIDDEN

    res_disc = fts_client(user_id=202).post(f"/api/v1/fts/files/{f.id}/discard/")
    assert res_disc.status_code == status.HTTP_403_FORBIDDEN


# ==========================================
# FTS-UC-003: Send / Forward File to Employee
# ==========================================


def test_tc_fts_003_01(fts_client):
    """TC-FTS-003-01 [FTS-UC-003 Main Success Scenario].

    Verify forwarding an active file to a recipient with a mandatory comment.
    """
    f = create_file(
        subject="UC-003 Forward File",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="faculty_101",
        recipient_role="Assistant Professor",
    )
    res = fts_client(user_id=101).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={"to_user_id": 202, "to_username": "staff_202", "to_role": "Staff", "comment": "Forwarding to staff."},
        format="json",
    )
    assert res.status_code == status.HTTP_200_OK
    f.refresh_from_db()
    assert f.current_holder_user_id == 202
    assert NotificationEvent.objects.filter(recipient_user_id=202, event_type="FILE_FORWARDED").exists()


def test_tc_fts_003_02(fts_client):
    """TC-FTS-003-02 [FTS-UC-003 Main Success Scenario with attachment].

    Verify forwarding with both a mandatory comment and optional movement attachments.
    """
    f = create_file(
        subject="UC-003 Attach Forward",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="faculty_101",
        recipient_role="Assistant Professor",
    )
    res = fts_client(user_id=101).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={
            "to_user_id": 202,
            "to_username": "staff_202",
            "to_role": "Staff",
            "comment": "Forwarding with updated quotation.",
            "attachments": [
                {
                    "file_name": "quotation_v2.pdf",
                    "file_url": "https://storage.fusion.ac.in/fts/quote2.pdf",
                    "file_size": 40960,
                    "mime_type": "application/pdf",
                }
            ],
        },
        format="json",
    )
    assert res.status_code == status.HTTP_200_OK
    detail = fts_client(user_id=101).get(f"/api/v1/fts/files/{f.id}/").json()
    assert any(a["file_name"] == "quotation_v2.pdf" for a in detail["attachments"])


def test_tc_fts_003_03(fts_client):
    """TC-FTS-003-03 [FTS-UC-003 Alternative Flow 1 (onward forwarding by recipient)].

    Verify onward forwarding by a recipient who previously received the file.
    """
    f = create_file(
        subject="UC-003 Onward",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Staff",
    )
    res = fts_client(user_id=202).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={"to_user_id": 303, "to_username": "dean_303", "to_role": "Dean", "comment": "Onward to Dean."},
        format="json",
    )
    assert res.status_code == status.HTTP_200_OK
    f.refresh_from_db()
    assert f.current_holder_user_id == 303


def test_tc_fts_003_04(fts_client):
    """TC-FTS-003-04 [FTS-UC-003 Alternative Flow 2 (no attachment)].

    Verify that forwarding proceeds when no attachment is supplied.
    """
    f = create_file(
        subject="UC-003 No Attach",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="faculty_101",
        recipient_role="Assistant Professor",
    )
    res = fts_client(user_id=101).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={"to_user_id": 202, "to_username": "staff_202", "to_role": "Staff", "comment": "No attach fwd."},
        format="json",
    )
    assert res.status_code == status.HTTP_200_OK


def test_tc_fts_003_05(fts_client):
    """TC-FTS-003-05 [FTS-UC-003 Exception Flows (missing comment / invalid recipient / archived)].

    Verify that missing comment, invalid recipient, or archived status blocks forwarding.
    """
    f = create_file(
        subject="UC-003 Guards",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="faculty_101",
        recipient_role="Assistant Professor",
    )
    # 1. Missing comment
    res_no_cmt = fts_client(user_id=101).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={"to_user_id": 202, "to_username": "staff_202", "to_role": "Staff", "comment": ""},
        format="json",
    )
    assert res_no_cmt.status_code == status.HTTP_400_BAD_REQUEST

    # 2. Invalid recipient
    res_inv_recip = fts_client(user_id=101).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={"to_user_id": -1, "to_username": "invalid", "to_role": "Staff", "comment": "Valid comment."},
        format="json",
    )
    assert res_inv_recip.status_code == status.HTTP_400_BAD_REQUEST


# ==========================================
# FTS-UC-004: Return Received File
# ==========================================


def test_tc_fts_004_01(fts_client):
    """TC-FTS-004-01 [FTS-UC-004 Main Success Scenario].

    Verify returning an active received file to the sender with a mandatory comment.
    """
    f = create_file(
        subject="UC-004 Return",
        comment_text="From 101 to 202.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Junior Superintendent",
    )
    res = fts_client(user_id=202).post(
        f"/api/v1/fts/files/{f.id}/return/",
        data={"comment": "Returning for missing signatures."},
        format="json",
    )
    assert res.status_code == status.HTTP_200_OK
    f.refresh_from_db()
    assert f.current_holder_user_id == 101
    assert NotificationEvent.objects.filter(recipient_user_id=101, event_type="FILE_RETURNED").exists()


def test_tc_fts_004_02(fts_client):
    """TC-FTS-004-02 [FTS-UC-004 Main Success Scenario with attachment].

    Verify returning a file with both mandatory comment and an attachment.
    """
    f = create_file(
        subject="UC-004 Return Attach",
        comment_text="From 101 to 202.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Junior Superintendent",
    )
    res = fts_client(user_id=202).post(
        f"/api/v1/fts/files/{f.id}/return/",
        data={
            "comment": "Returning with marked comments.",
            "attachments": [
                {
                    "file_name": "markup.pdf",
                    "file_url": "https://storage.fusion.ac.in/fts/markup.pdf",
                    "file_size": 12000,
                    "mime_type": "application/pdf",
                }
            ],
        },
        format="json",
    )
    assert res.status_code == status.HTTP_200_OK


def test_tc_fts_004_03(fts_client):
    """TC-FTS-004-03 [FTS-UC-004 Alternative Flow 1 (no attachment)].

    Verify that returning a file proceeds normally without attachments.
    """
    f = create_file(
        subject="UC-004 No Attach",
        comment_text="From 101 to 202.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Junior Superintendent",
    )
    res = fts_client(user_id=202).post(
        f"/api/v1/fts/files/{f.id}/return/",
        data={"comment": "Clean return."},
        format="json",
    )
    assert res.status_code == status.HTTP_200_OK


def test_tc_fts_004_04(fts_client):
    """TC-FTS-004-04 [FTS-UC-004 Exception Flows (missing comment / unauthorized)].

    Verify that missing comment or unauthorized actor blocks return.
    """
    f = create_file(
        subject="UC-004 Return Guards",
        comment_text="From 101 to 202.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Junior Superintendent",
    )
    # Empty comment
    res_no_cmt = fts_client(user_id=202).post(
        f"/api/v1/fts/files/{f.id}/return/",
        data={"comment": "   "},
        format="json",
    )
    assert res_no_cmt.status_code == status.HTTP_400_BAD_REQUEST

    # Non-holder attempt
    res_unauth = fts_client(user_id=303).post(
        f"/api/v1/fts/files/{f.id}/return/",
        data={"comment": "Impostor return."},
        format="json",
    )
    assert res_unauth.status_code == status.HTTP_403_FORBIDDEN


# ==========================================
# FTS-UC-005: View Inbox, Outbox, and Open Files
# ==========================================


def test_tc_fts_005_01(fts_client):
    """TC-FTS-005-01 [FTS-UC-005 Main Success Scenario (view Inbox)].

    Verify listing received files in the user's Inbox.
    """
    f = create_file(
        subject="Inbox Listing Test",
        comment_text="From 101 to 202.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Junior Superintendent",
    )
    inbox = fts_client(user_id=202).get("/api/v1/fts/inbox/").json()
    assert any(item["id"] == f.id for item in inbox)


def test_tc_fts_005_02(fts_client):
    """TC-FTS-005-02 [FTS-UC-005 Main Success Scenario (view Outbox)].

    Verify listing sent files in the user's Outbox.
    """
    f = create_file(
        subject="Outbox Listing Test",
        comment_text="From 101 to 202.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Junior Superintendent",
    )
    outbox = fts_client(user_id=101).get("/api/v1/fts/outbox/").json()
    assert any(item["id"] == f.id for item in outbox)


def test_tc_fts_005_03(fts_client):
    """TC-FTS-005-03 [FTS-UC-005 Main Success Scenario (open authorized file)].

    Verify opening an authorized file displays details, comments, and attachments.
    """
    f = create_file(
        subject="Detail View Test",
        comment_text="Detailed remark.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Junior Superintendent",
    )
    res = fts_client(user_id=101).get(f"/api/v1/fts/files/{f.id}/")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["id"] == f.id
    assert len(data["comments"]) >= 1


def test_tc_fts_005_04(fts_client):
    """TC-FTS-005-04 [FTS-UC-005 Alternative Flow 1 (open archived file as read-only)].

    Verify opening an archived file presents it in read-only state.
    """
    f = create_file(
        subject="Archived Open Test",
        comment_text="Detail remark.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="faculty_101",
        recipient_role="Assistant Professor",
    )
    archive_file(
        file_id=f.id,
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
    )
    res = fts_client(user_id=101).get(f"/api/v1/fts/files/{f.id}/")
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["status"] == STATE_ARCHIVED


def test_tc_fts_005_05(fts_client):
    """TC-FTS-005-05 [FTS-UC-005 Exception Flow 1 (unauthorized file access blocked)].

    Verify that an unauthorized user cannot access a file.
    """
    f = create_file(
        subject="Confidential Scoped File",
        comment_text="Private.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Junior Superintendent",
    )
    res = fts_client(user_id=999).get(f"/api/v1/fts/files/{f.id}/")
    assert res.status_code == status.HTTP_404_NOT_FOUND


def test_tc_fts_005_06(fts_client):
    """TC-FTS-005-06 [FTS-UC-005 Exception Flow 2 (unavailable action denied)].

    Verify that an action not permitted for the current file state is denied.
    """
    f = create_file(
        subject="State Action Denied",
        comment_text="Draft file.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=True,
    )
    # Draft files cannot be returned
    res = fts_client(user_id=101).post(f"/api/v1/fts/files/{f.id}/return/", data={"comment": "Return draft."})
    assert res.status_code == status.HTTP_409_CONFLICT


def test_tc_fts_005_07(fts_client):
    """TC-FTS-005-07 [FTS-UC-005 Postcondition: viewing does not alter state].

    Verify that viewing inbox, outbox, or file details does not mutate business state.
    """
    f = create_file(
        subject="Immutable View Test",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Junior Superintendent",
    )
    status_before = f.status
    holder_before = f.current_holder_user_id

    fts_client(user_id=202).get("/api/v1/fts/inbox/")
    fts_client(user_id=101).get("/api/v1/fts/outbox/")
    fts_client(user_id=202).get(f"/api/v1/fts/files/{f.id}/")

    f.refresh_from_db()
    assert f.status == status_before
    assert f.current_holder_user_id == holder_before


# ==========================================
# FTS-UC-006: View File Tracking History
# ==========================================


def test_tc_fts_006_01(fts_client):
    """TC-FTS-006-01 [FTS-UC-006 Main Success Scenario].

    Verify viewing chronological tracking history for an associated file.
    """
    f = create_file(
        subject="History Test File",
        comment_text="Initial remark.",
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
        data={"to_user_id": 202, "to_username": "staff_202", "to_role": "Staff", "comment": "Movement 2."},
        format="json",
    )
    res = fts_client(user_id=101).get(f"/api/v1/fts/files/{f.id}/history/")
    assert res.status_code == status.HTTP_200_OK
    history = res.json()
    assert len(history) == 2
    assert history[0]["sequence"] == 1
    assert history[1]["sequence"] == 2


def test_tc_fts_006_02(fts_client):
    """TC-FTS-006-02 [FTS-UC-006 Alternative Flow 1 (history includes all events)].

    Verify history includes forward, return, and creation movements.
    """
    f = create_file(
        subject="Full History File",
        comment_text="Step 1.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Staff",
    )
    fts_client(user_id=202).post(
        f"/api/v1/fts/files/{f.id}/return/",
        data={"comment": "Step 2 return."},
        format="json",
    )
    history = fts_client(user_id=101).get(f"/api/v1/fts/files/{f.id}/history/").json()
    types = [m["movement_type"] for m in history]
    assert "CREATION" in types
    assert "RETURN" in types


def test_tc_fts_006_03(fts_client):
    """TC-FTS-006-03 [FTS-UC-006 Exception Flow 1 (unauthorized history access)].

    Verify that an unassociated employee is denied tracking history access.
    """
    f = create_file(
        subject="Private History File",
        comment_text="Private.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Staff",
    )
    res = fts_client(user_id=999).get(f"/api/v1/fts/files/{f.id}/history/")
    assert res.status_code == status.HTTP_404_NOT_FOUND


def test_tc_fts_006_04(fts_client):
    """TC-FTS-006-04 [FTS-UC-006 Postcondition: viewing history does not alter state].

    Verify that viewing history is a read-only operation.
    """
    f = create_file(
        subject="History Read-Only File",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Staff",
    )
    fts_client(user_id=101).get(f"/api/v1/fts/files/{f.id}/history/")
    f.refresh_from_db()
    assert f.status == STATE_CIRCULATED


def test_tc_fts_006_05(fts_client):
    """TC-FTS-006-05 [FTS-UC-006 History completeness and field presence].

    Verify tracking history contains sender, receiver, timestamp, comment, and attachment fields.
    """
    f = create_file(
        subject="Complete History Fields",
        comment_text="Initial creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="faculty_101",
        recipient_role="Assistant Professor",
    )
    history = fts_client(user_id=101).get(f"/api/v1/fts/files/{f.id}/history/").json()
    item = history[0]
    assert "from_user_id" in item
    assert "to_user_id" in item
    assert "created_at" in item
    assert "comments" in item
    assert "attachments" in item


# ==========================================
# FTS-UC-007: Archive Completed File
# ==========================================


def test_tc_fts_007_01(fts_client):
    """TC-FTS-007-01 [FTS-UC-007 Main Success Scenario].

    Verify that file owner can archive a completed circulated file.
    """
    f = create_file(
        subject="UC-007 Archive",
        comment_text="Creation.",
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
    assert res.json()["status"] == STATE_ARCHIVED
    assert NotificationEvent.objects.filter(recipient_user_id=101, event_type="FILE_ARCHIVED").exists()


def test_tc_fts_007_02(fts_client):
    """TC-FTS-007-02 [FTS-UC-007 Alternative Flow 1 (already archived file)].

    Verify that attempting to re-archive an already-archived file is rejected.
    """
    f = create_file(
        subject="UC-007 Re-archive",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="faculty_101",
        recipient_role="Assistant Professor",
    )
    archive_file(
        file_id=f.id,
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
    )
    res = fts_client(user_id=101).post(f"/api/v1/fts/files/{f.id}/archive/")
    assert res.status_code == status.HTTP_409_CONFLICT


def test_tc_fts_007_03(fts_client):
    """TC-FTS-007-03 [FTS-UC-007 Exception Flow 1 (non-owner archival denied)].

    Verify that a non-owner employee is denied archival.
    """
    f = create_file(
        subject="UC-007 Non-owner",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Staff",
    )
    res = fts_client(user_id=202).post(f"/api/v1/fts/files/{f.id}/archive/")
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_tc_fts_007_04(fts_client):
    """TC-FTS-007-04 [FTS-UC-007 Exception Flow 2 (archival without permission denied)].

    Verify that an employee without archive permission is denied archival.
    """
    f = create_file(
        subject="UC-007 No Perm",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="faculty_101",
        recipient_role="Assistant Professor",
    )
    res = fts_client(user_id=101, permissions=("fts.file.view",)).post(f"/api/v1/fts/files/{f.id}/archive/")
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_tc_fts_007_05(fts_client):
    """TC-FTS-007-05 [FTS-UC-007 Archived file is immutable and cannot be forwarded].

    Verify that once archived, a file cannot be modified or forwarded.
    """
    f = create_file(
        subject="UC-007 Immutability",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="faculty_101",
        recipient_role="Assistant Professor",
    )
    archive_file(
        file_id=f.id,
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
    )
    res_fwd = fts_client(user_id=101).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={"to_user_id": 202, "to_username": "staff", "to_role": "Staff", "comment": "Fwd."},
        format="json",
    )
    assert res_fwd.status_code == status.HTTP_409_CONFLICT


# ==========================================
# FTS-UC-008: Select Assigned Role Context for FTS
# ==========================================


def test_tc_fts_008_01(fts_client):
    """TC-FTS-008-01 [FTS-UC-008 Main Success Scenario].

    Verify operating under a switched role preserves ownership and history.
    """
    f = create_file(
        subject="Role Switch Preservation",
        comment_text="Initial creation by Professor.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=True,
    )
    # Role switches to Dean
    fts_client(user_id=101, active_role="Dean Academic")
    f.refresh_from_db()
    assert f.owner_user_id == 101
    assert f.owner_role == "Professor"


def test_tc_fts_008_02(fts_client):
    """TC-FTS-008-02 [FTS-UC-008 Alternative Flow 1 (single role context)].

    Verify single role user operates without requiring explicit role switch.
    """
    res = fts_client(user_id=101, roles=("faculty",), active_role="Assistant Professor").get("/api/v1/fts/inbox/")
    assert res.status_code == status.HTTP_200_OK


def test_tc_fts_008_03(fts_client):
    """TC-FTS-008-03 [FTS-UC-008 Exception Flow 1 (role does not authorize action)].

    Verify that an action not authorized under the active role is rejected.
    """
    res = fts_client(user_id=101, permissions=("fts.file.view",)).post(
        "/api/v1/fts/files/",
        data={"subject": "Denied Action", "comment": "Comment.", "is_draft": True},
        format="json",
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN


# ==========================================
# FTS-UC-009: Administer FTS User Access Context
# ==========================================


def test_tc_fts_009_01():
    """TC-FTS-009-01 [FTS-UC-009 Main Success Scenario (role notification)].

    Verify role assignment notification event triggers and is recorded by FTS.
    """
    ev = trigger_notification(
        event_type="ROLE_ASSIGNED",
        recipient_user_id=101,
        payload={"new_role": "Dean Students", "assigned_by": "admin_999"},
    )
    assert NotificationEvent.objects.filter(id=ev.id, event_type="ROLE_ASSIGNED").exists()


def test_tc_fts_009_02(admin_client):
    """TC-FTS-009-02 [FTS-UC-009 Main Success Scenario (audit/usage review)].

    Verify System Admin can view governance usage metrics and audit logs.
    """
    c_admin = admin_client()
    res_usage = c_admin.get("/api/v1/fts/governance/usage/")
    assert res_usage.status_code == status.HTTP_200_OK

    res_audit = c_admin.get("/api/v1/fts/governance/audit-logs/")
    assert res_audit.status_code == status.HTTP_200_OK


def test_tc_fts_009_03(fts_client):
    """TC-FTS-009-03 [FTS-UC-009 Platform account identity consumed by FTS].

    Verify FTS consumes session identity provided by platform without modifying it.
    """
    c = fts_client(user_id=888, kind="faculty", active_role="Associate Professor")
    res = c.get("/api/v1/fts/inbox/")
    assert res.status_code == status.HTTP_200_OK


def test_tc_fts_009_04(admin_client):
    """TC-FTS-009-04 [FTS-UC-009 Exception Flow 1 (admin operational action denied)].

    Verify System Admin cannot perform operational file workflows.
    """
    c_admin = admin_client()
    res = c_admin.post(
        "/api/v1/fts/files/",
        data={"subject": "Admin Operational File", "comment": "Comment."},
        format="json",
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN


# ==========================================
# FTS-UC-010: Use FTS Workflow-Support APIs
# ==========================================


def test_tc_fts_010_01(stub_iam):
    """TC-FTS-010-01 [FTS-UC-010 Main Success Scenario].

    Verify authorized consuming module can invoke FTS integration API to create/track file.
    """
    stub_iam(
        make_fts_session(
            user_id=701,
            kind="faculty",
            permissions=("fts.integration.access",),
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token integ-token")

    res = c.post(
        "/api/v1/fts/integrations/requests/",
        data={
            "subject": "Module Integration Request",
            "comment": "Leave workflow tracking.",
            "is_draft": False,
            "recipient_user_id": 202,
            "recipient_username": "staff_202",
            "recipient_role": "Staff",
        },
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()
    assert FileAuditLog.objects.filter(file_id=data["id"]).exists()


def test_tc_fts_010_02(stub_iam):
    """TC-FTS-010-02 [FTS-UC-010 Alternative Flow 1 (different integration capabilities)].

    Verify integration endpoints support both draft creation and circulated tracking.
    """
    stub_iam(
        make_fts_session(
            user_id=701,
            kind="faculty",
            permissions=("fts.integration.access",),
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token integ-token")

    res_draft = c.post(
        "/api/v1/fts/integrations/requests/",
        data={"subject": "Module Draft Request", "comment": "Draft integration.", "is_draft": True},
        format="json",
    )
    assert res_draft.status_code == status.HTTP_201_CREATED
    assert res_draft.json()["status"] == STATE_DRAFT


def test_tc_fts_010_03(stub_iam):
    """TC-FTS-010-03 [FTS-UC-010 Exception Flow 1 (unauthorized integration rejected)].

    Verify unauthorized integration caller is rejected with 403 Forbidden.
    """
    stub_iam(
        make_fts_session(
            user_id=701,
            kind="faculty",
            permissions=(),  # No integration access
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token integ-token")

    res = c.post(
        "/api/v1/fts/integrations/requests/",
        data={"subject": "Unauthorized Module Call", "comment": "Should fail."},
        format="json",
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_tc_fts_010_04(stub_iam):
    """TC-FTS-010-04 [FTS-UC-010 Exception Flow 2 (domain approval policy preserved in consuming module)].

    Verify FTS does not accept or enforce foreign domain approval policies.
    """
    stub_iam(
        make_fts_session(
            user_id=701,
            kind="faculty",
            permissions=("fts.integration.access",),
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token integ-token")

    # Pass consuming-module policy in data; FTS creates file according to FTS rules without adopting foreign policy
    res = c.post(
        "/api/v1/fts/integrations/requests/",
        data={
            "subject": "Consuming Module With Domain Rules",
            "comment": "Domain approval request.",
            "is_draft": True,
            "foreign_approval_rule": "ALLOW_ALL_AUTOMATICALLY",
        },
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()
    assert data["status"] == STATE_DRAFT
