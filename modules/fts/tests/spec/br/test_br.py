"""Specification tests for Business Rules (BR) strategy.

Generated from frozen BR_DESIGN.json.
Coverage: BR-FTS-001 through BR-FTS-014 (38 cases).
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
from modules.fts.models.files import File
from modules.fts.services.archival import archive_file
from modules.fts.services.files import create_file
from modules.fts.tests.conftest import make_fts_session

pytestmark = pytest.mark.django_db


def test_tc_br_fts_001_01(fts_client):
    """TC-BR-FTS-001-01 [BR-FTS-001 authorized-employee-permitted].

    Verify that an authorized Institute Employee (Faculty/Staff) can perform an
    operational file action (file creation).
    """
    res = fts_client(user_id=101, kind="faculty", active_role="Assistant Professor").post(
        "/api/v1/fts/files/",
        data={
            "subject": "BR-001 Faculty Requisition",
            "comment": "Initial mandatory remark.",
            "is_draft": True,
        },
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()
    assert data["status"] == STATE_DRAFT
    assert File.objects.filter(id=data["id"]).exists()


def test_tc_br_fts_001_02(admin_client):
    """TC-BR-FTS-001-02 [BR-FTS-001 system-admin-blocked].

    Verify that a System Admin account cannot perform operational file-processing
    actions (e.g., file creation).
    """
    res = admin_client().post(
        "/api/v1/fts/files/",
        data={
            "subject": "BR-001 Admin Operational Attempt",
            "comment": "Admin trying operational action.",
            "is_draft": True,
        },
        format="json",
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_tc_br_fts_002_01(fts_client):
    """TC-BR-FTS-002-01 [BR-FTS-002 ownership-preserved-after-role-switch].

    Verify that switching role context does not change the file owner attribute
    on files previously created.
    """
    f = create_file(
        subject="BR-002 File",
        comment_text="Initial comment by Professor.",
        actor_user_id=101,
        actor_username="prof_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Junior Superintendent",
    )
    orig_owner_id = f.owner_user_id
    orig_owner_username = f.owner_username
    orig_owner_role = f.owner_role

    # User 101 switches active role to "HOD (CSE)"
    fts_client(user_id=101, active_role="HOD (CSE)")
    f.refresh_from_db()
    assert f.owner_user_id == orig_owner_id
    assert f.owner_username == orig_owner_username
    assert f.owner_role == orig_owner_role


def test_tc_br_fts_002_02(fts_client):
    """TC-BR-FTS-002-02 [BR-FTS-002 audit-history-preserved-after-role-switch].

    Verify that switching role context does not alter previously recorded audit
    history entries.
    """
    f = create_file(
        subject="BR-002 Audit File",
        comment_text="Initial creation.",
        actor_user_id=101,
        actor_username="prof_101",
        actor_role="Professor",
        is_draft=True,
    )
    audit_entry = FileAuditLog.objects.filter(file_id=f.id, action="FILE_CREATED").first()
    assert audit_entry is not None
    orig_role = audit_entry.actor_role
    orig_time = audit_entry.timestamp

    # Role switch occurs
    fts_client(user_id=101, active_role="Dean R&D")
    audit_entry.refresh_from_db()
    assert audit_entry.actor_role == orig_role
    assert audit_entry.timestamp == orig_time


def test_tc_br_fts_003_01(fts_client):
    """TC-BR-FTS-003-01 [BR-FTS-003 circulated-file-contents-retained].

    Verify that comments and attachments added to a circulated file are retained
    and not deleted.
    """
    f = create_file(
        subject="BR-003 Retention File",
        comment_text="Initial circulated remark.",
        actor_user_id=101,
        actor_username="prof_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Junior Superintendent",
        attachments=[
            {
                "file_name": "memo.pdf",
                "file_url": "https://storage.fusion.ac.in/fts/memo.pdf",
                "file_size": 2048,
                "mime_type": "application/pdf",
            }
        ],
    )
    res = fts_client(user_id=101).get(f"/api/v1/fts/files/{f.id}/")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert len(data["comments"]) >= 1
    assert any(c["comment_text"] == "Initial circulated remark." for c in data["comments"])
    assert len(data["attachments"]) >= 1
    assert any(a["file_name"] == "memo.pdf" for a in data["attachments"])


def test_tc_br_fts_003_02(fts_client):
    """TC-BR-FTS-003-02 [BR-FTS-003 circulated-file-not-deleted].

    Verify that a circulated file cannot be deleted (e.g., via draft-discard or
    any deletion operation).
    """
    f = create_file(
        subject="BR-003 No Deletion",
        comment_text="Circulated file.",
        actor_user_id=101,
        actor_username="prof_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Junior Superintendent",
    )
    res = fts_client(user_id=101).post(f"/api/v1/fts/files/{f.id}/discard/")
    assert res.status_code == status.HTTP_409_CONFLICT
    f.refresh_from_db()
    assert f.status == STATE_CIRCULATED


def test_tc_br_fts_004_01(fts_client):
    """TC-BR-FTS-004-01 [BR-FTS-004 creation-blocked-without-comment].

    Verify that file creation is blocked when no initial comment is provided.
    """
    res = fts_client(user_id=101).post(
        "/api/v1/fts/files/",
        data={"subject": "Missing Comment", "comment": "   ", "is_draft": True},
        format="json",
    )
    assert res.status_code == status.HTTP_400_BAD_REQUEST


def test_tc_br_fts_004_02(fts_client):
    """TC-BR-FTS-004-02 [BR-FTS-004 creation-accepted-with-comment].

    Verify that file creation succeeds when an initial mandatory comment is provided.
    """
    res = fts_client(user_id=101).post(
        "/api/v1/fts/files/",
        data={"subject": "Valid File", "comment": "Valid initial comment.", "is_draft": True},
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED
    assert res.json()["status"] == STATE_DRAFT


def test_tc_br_fts_005_01(fts_client):
    """TC-BR-FTS-005-01 [BR-FTS-005 draft-save-permitted-pre-submission].

    Verify that saving a draft is permitted before submission.
    """
    res = fts_client(user_id=101).post(
        "/api/v1/fts/files/",
        data={"subject": "Pre-submission Draft", "comment": "Draft comment.", "is_draft": True},
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED
    assert res.json()["status"] == STATE_DRAFT


def test_tc_br_fts_005_02(fts_client):
    """TC-BR-FTS-005-02 [BR-FTS-005 draft-edit-permitted-pre-submission].

    Verify that editing a saved draft is permitted before submission.
    """
    f = create_file(
        subject="Editable Draft",
        comment_text="Original comment.",
        actor_user_id=101,
        actor_username="prof_101",
        actor_role="Professor",
        is_draft=True,
    )
    res = fts_client(user_id=101).put(
        f"/api/v1/fts/files/{f.id}/",
        data={"subject": "Updated Draft Subject", "comment": "Updated comment."},
        format="json",
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["subject"] == "Updated Draft Subject"


def test_tc_br_fts_005_03(fts_client):
    """TC-BR-FTS-005-03 [BR-FTS-005 draft-discard-permitted-pre-submission].

    Verify that discarding a draft is permitted before submission.
    """
    f = create_file(
        subject="Discardable Draft",
        comment_text="Draft to discard.",
        actor_user_id=101,
        actor_username="prof_101",
        actor_role="Professor",
        is_draft=True,
    )
    res = fts_client(user_id=101).post(f"/api/v1/fts/files/{f.id}/discard/")
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["status"] == STATE_DISCARDED


def test_tc_br_fts_005_04(fts_client):
    """TC-BR-FTS-005-04 [BR-FTS-005 draft-discard-blocked-post-circulation].

    Verify that draft discard/deletion is blocked after the file has been circulated.
    """
    f = create_file(
        subject="Circulated File Discard Attempt",
        comment_text="Initial comment.",
        actor_user_id=101,
        actor_username="prof_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Junior Superintendent",
    )
    res = fts_client(user_id=101).post(f"/api/v1/fts/files/{f.id}/discard/")
    assert res.status_code == status.HTTP_409_CONFLICT
    f.refresh_from_db()
    assert f.status == STATE_CIRCULATED


def test_tc_br_fts_006_01(fts_client):
    """TC-BR-FTS-006-01 [BR-FTS-006 forward-blocked-without-comment].

    Verify that forwarding a file is blocked when no movement comment is supplied.
    """
    f = create_file(
        subject="Forward Without Comment",
        comment_text="Initial comment.",
        actor_user_id=101,
        actor_username="prof_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="prof_101",
        recipient_role="Professor",
    )
    res = fts_client(user_id=101).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={"to_user_id": 202, "to_username": "staff_202", "to_role": "Staff", "comment": ""},
        format="json",
    )
    assert res.status_code == status.HTTP_400_BAD_REQUEST


def test_tc_br_fts_006_02(fts_client):
    """TC-BR-FTS-006-02 [BR-FTS-006 forward-accepted-with-comment].

    Verify that forwarding a file succeeds when a mandatory movement comment is provided.
    """
    f = create_file(
        subject="Forward With Comment",
        comment_text="Initial comment.",
        actor_user_id=101,
        actor_username="prof_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="prof_101",
        recipient_role="Professor",
    )
    res = fts_client(user_id=101).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={
            "to_user_id": 202,
            "to_username": "staff_202",
            "to_role": "Staff",
            "comment": "Valid movement comment.",
        },
        format="json",
    )
    assert res.status_code == status.HTTP_200_OK


def test_tc_br_fts_006_03(fts_client):
    """TC-BR-FTS-006-03 [BR-FTS-006 return-blocked-without-comment].

    Verify that returning a file is blocked when no movement comment is supplied.
    """
    f = create_file(
        subject="Return Without Comment",
        comment_text="Initial comment from 101 to 202.",
        actor_user_id=101,
        actor_username="prof_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Junior Superintendent",
    )
    res = fts_client(user_id=202).post(
        f"/api/v1/fts/files/{f.id}/return/",
        data={"comment": "   "},
        format="json",
    )
    assert res.status_code == status.HTTP_400_BAD_REQUEST


def test_tc_br_fts_006_04(fts_client):
    """TC-BR-FTS-006-04 [BR-FTS-006 return-accepted-with-comment].

    Verify that returning a file succeeds when a mandatory movement comment is provided.
    """
    f = create_file(
        subject="Return With Comment",
        comment_text="Initial comment from 101 to 202.",
        actor_user_id=101,
        actor_username="prof_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Junior Superintendent",
    )
    res = fts_client(user_id=202).post(
        f"/api/v1/fts/files/{f.id}/return/",
        data={"comment": "Returning for correction."},
        format="json",
    )
    assert res.status_code == status.HTTP_200_OK


def test_tc_br_fts_007_01(fts_client):
    """TC-BR-FTS-007-01 [BR-FTS-007 valid-institute-employee-recipient-accepted].

    Verify that sending/forwarding a file to a valid Institute Employee is accepted.
    """
    f = create_file(
        subject="Valid Recipient Test",
        comment_text="Initial.",
        actor_user_id=101,
        actor_username="prof_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="prof_101",
        recipient_role="Professor",
    )
    res = fts_client(user_id=101).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={
            "to_user_id": 202,
            "to_username": "staff_202",
            "to_role": "Junior Superintendent",
            "comment": "Sending to valid employee.",
        },
        format="json",
    )
    assert res.status_code == status.HTTP_200_OK
    f.refresh_from_db()
    assert f.current_holder_user_id == 202


def test_tc_br_fts_007_02(fts_client):
    """TC-BR-FTS-007-02 [BR-FTS-007 non-employee-recipient-rejected].

    Verify that forwarding to an invalid recipient (e.g., recipient_user_id <= 0 or None) is rejected.
    """
    f = create_file(
        subject="Invalid Recipient Test",
        comment_text="Initial.",
        actor_user_id=101,
        actor_username="prof_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="prof_101",
        recipient_role="Professor",
    )
    res = fts_client(user_id=101).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={"to_user_id": 0, "to_username": "invalid", "to_role": "None", "comment": "Invalid to_id."},
        format="json",
    )
    assert res.status_code == status.HTTP_400_BAD_REQUEST


def test_tc_br_fts_007_03(fts_client):
    """TC-BR-FTS-007-03 [BR-FTS-007 return-routed-to-sender].

    Verify that a return action routes the file back to the sender of the received movement.
    """
    f = create_file(
        subject="Route to Sender Test",
        comment_text="101 sends to 202.",
        actor_user_id=101,
        actor_username="prof_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Junior Superintendent",
    )
    res = fts_client(user_id=202).post(
        f"/api/v1/fts/files/{f.id}/return/",
        data={"comment": "Returning back to sender."},
        format="json",
    )
    assert res.status_code == status.HTTP_200_OK
    f.refresh_from_db()
    assert f.current_holder_user_id == 101


def test_tc_br_fts_008_01(fts_client):
    """TC-BR-FTS-008-01 [BR-FTS-008 forward-event-recorded-chronologically].

    Verify that a successful forward event is appended to the file's chronological
    movement history with all required fields.
    """
    f = create_file(
        subject="Chronological Forward",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="prof_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="prof_101",
        recipient_role="Professor",
    )
    fts_client(user_id=101).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={"to_user_id": 202, "to_username": "staff_202", "to_role": "Staff", "comment": "Fwd remark."},
        format="json",
    )
    res_hist = fts_client(user_id=101).get(f"/api/v1/fts/files/{f.id}/history/")
    assert res_hist.status_code == status.HTTP_200_OK
    history = res_hist.json()
    assert len(history) == 2
    assert history[0]["sequence"] == 1
    assert history[1]["sequence"] == 2
    assert history[1]["movement_type"] == "FORWARD"
    assert history[1]["from_user_id"] == 101
    assert history[1]["to_user_id"] == 202


def test_tc_br_fts_008_02(fts_client):
    """TC-BR-FTS-008-02 [BR-FTS-008 return-event-recorded-chronologically].

    Verify that a successful return event is appended to the file's chronological
    movement history with all required fields.
    """
    f = create_file(
        subject="Chronological Return",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="prof_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Junior Superintendent",
    )
    fts_client(user_id=202).post(
        f"/api/v1/fts/files/{f.id}/return/",
        data={"comment": "Return remark."},
        format="json",
    )
    res_hist = fts_client(user_id=101).get(f"/api/v1/fts/files/{f.id}/history/")
    assert res_hist.status_code == status.HTTP_200_OK
    history = res_hist.json()
    assert len(history) == 2
    assert history[1]["sequence"] == 2
    assert history[1]["movement_type"] == "RETURN"
    assert history[1]["from_user_id"] == 202
    assert history[1]["to_user_id"] == 101


def test_tc_br_fts_009_01(fts_client):
    """TC-BR-FTS-009-01 [BR-FTS-009 associated-user-can-access-file].

    Verify that an authorized user associated with a file can open and read its
    contents and history.
    """
    f = create_file(
        subject="Associated Access",
        comment_text="Initial.",
        actor_user_id=101,
        actor_username="prof_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Junior Superintendent",
    )
    res_owner = fts_client(user_id=101).get(f"/api/v1/fts/files/{f.id}/")
    assert res_owner.status_code == status.HTTP_200_OK

    res_recipient = fts_client(user_id=202).get(f"/api/v1/fts/files/{f.id}/")
    assert res_recipient.status_code == status.HTTP_200_OK


def test_tc_br_fts_009_02(fts_client):
    """TC-BR-FTS-009-02 [BR-FTS-009 non-associated-user-blocked].

    Verify that a user not associated with a file cannot access it.
    """
    f = create_file(
        subject="Private File",
        comment_text="Initial.",
        actor_user_id=101,
        actor_username="prof_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Junior Superintendent",
    )
    res_unassoc = fts_client(user_id=999).get(f"/api/v1/fts/files/{f.id}/")
    # Status code 404 per anti-enumeration conventions
    assert res_unassoc.status_code == status.HTTP_404_NOT_FOUND


def test_tc_br_fts_009_03(fts_client):
    """TC-BR-FTS-009-03 [BR-FTS-009 archived-file-readable-to-authorized-user].

    Verify that an archived file remains readable to authorized associated users.
    """
    f = create_file(
        subject="Archived Readable",
        comment_text="Initial.",
        actor_user_id=101,
        actor_username="prof_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Junior Superintendent",
    )
    archive_file(
        file_id=f.id,
        actor_user_id=101,
        actor_username="prof_101",
        actor_role="Professor",
    )
    res_recip = fts_client(user_id=202).get(f"/api/v1/fts/files/{f.id}/")
    assert res_recip.status_code == status.HTTP_200_OK
    assert res_recip.json()["status"] == STATE_ARCHIVED


def test_tc_br_fts_010_01(fts_client):
    """TC-BR-FTS-010-01 [BR-FTS-010 unauthorized-role-action-rejected].

    Verify that a user whose role does not permit a specific FTS action is blocked.
    """
    f = create_file(
        subject="Permission Guard File",
        comment_text="Initial.",
        actor_user_id=101,
        actor_username="prof_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Junior Superintendent",
    )
    # User 202 without fts.file.forward permission
    res = fts_client(user_id=202, permissions=("fts.file.view",)).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={"to_user_id": 303, "to_username": "dean", "to_role": "Dean", "comment": "No perm forward."},
        format="json",
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_tc_br_fts_010_02(fts_client):
    """TC-BR-FTS-010-02 [BR-FTS-010 authorized-role-action-permitted].

    Verify that a user with the correct role and file association can perform an authorized FTS action.
    """
    f = create_file(
        subject="Permitted Action File",
        comment_text="Initial.",
        actor_user_id=101,
        actor_username="prof_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Junior Superintendent",
    )
    res = fts_client(user_id=202, permissions=("fts.file.forward", "fts.file.view")).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={"to_user_id": 303, "to_username": "dean", "to_role": "Dean", "comment": "Authorized forward."},
        format="json",
    )
    assert res.status_code == status.HTTP_200_OK


def test_tc_br_fts_011_01(fts_client):
    """TC-BR-FTS-011-01 [BR-FTS-011 audit-log-creation-recorded].

    Verify that an audit record is created when a new file is created.
    """
    f = create_file(
        subject="Audit Creation Test",
        comment_text="Audit remark.",
        actor_user_id=101,
        actor_username="prof_101",
        actor_role="Professor",
        is_draft=True,
    )
    assert FileAuditLog.objects.filter(file_id=f.id, action="FILE_CREATED").exists()


def test_tc_br_fts_011_02(fts_client):
    """TC-BR-FTS-011-02 [BR-FTS-011 audit-log-forward-recorded].

    Verify that an audit record is appended when a file is forwarded.
    """
    f = create_file(
        subject="Audit Forward Test",
        comment_text="Audit remark.",
        actor_user_id=101,
        actor_username="prof_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="prof_101",
        recipient_role="Professor",
    )
    fts_client(user_id=101).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={"to_user_id": 202, "to_username": "staff_202", "to_role": "Staff", "comment": "Forwarding for audit."},
        format="json",
    )
    assert FileAuditLog.objects.filter(file_id=f.id, action="FILE_FORWARDED").exists()


def test_tc_br_fts_011_03(fts_client):
    """TC-BR-FTS-011-03 [BR-FTS-011 audit-log-archival-recorded].

    Verify that an audit record is appended when a file is archived.
    """
    f = create_file(
        subject="Audit Archival Test",
        comment_text="Audit remark.",
        actor_user_id=101,
        actor_username="prof_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="prof_101",
        recipient_role="Professor",
    )
    fts_client(user_id=101).post(f"/api/v1/fts/files/{f.id}/archive/")
    assert FileAuditLog.objects.filter(file_id=f.id, action="FILE_ARCHIVED").exists()


def test_tc_br_fts_011_04(fts_client):
    """TC-BR-FTS-011-04 [BR-FTS-011 prior-audit-history-not-rewritten].

    Verify that existing audit records are not rewritten or removed when new events occur.
    """
    f = create_file(
        subject="Audit Immutability Test",
        comment_text="Init.",
        actor_user_id=101,
        actor_username="prof_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="prof_101",
        recipient_role="Professor",
    )
    initial_log_count = FileAuditLog.objects.filter(file_id=f.id).count()
    first_log_id = FileAuditLog.objects.filter(file_id=f.id).first().id

    fts_client(user_id=101).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={"to_user_id": 202, "to_username": "staff_202", "to_role": "Staff", "comment": "Second action."},
        format="json",
    )
    assert FileAuditLog.objects.filter(file_id=f.id).count() == initial_log_count + 1
    assert FileAuditLog.objects.filter(id=first_log_id).exists()


def test_tc_br_fts_012_01(fts_client):
    """TC-BR-FTS-012-01 [BR-FTS-012 owner-can-archive].

    Verify that the file owner can archive a completed circulated file.
    """
    f = create_file(
        subject="Owner Archive Test",
        comment_text="Init.",
        actor_user_id=101,
        actor_username="prof_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Junior Superintendent",
    )
    res = fts_client(user_id=101).post(f"/api/v1/fts/files/{f.id}/archive/")
    assert res.status_code == status.HTTP_200_OK
    f.refresh_from_db()
    assert f.status == STATE_ARCHIVED


def test_tc_br_fts_012_02(fts_client):
    """TC-BR-FTS-012-02 [BR-FTS-012 non-owner-cannot-archive].

    Verify that a non-owner Institute Employee cannot archive a file.
    """
    f = create_file(
        subject="Non-Owner Archive Test",
        comment_text="Init.",
        actor_user_id=101,
        actor_username="prof_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Junior Superintendent",
    )
    res = fts_client(user_id=202).post(f"/api/v1/fts/files/{f.id}/archive/")
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_tc_br_fts_012_03(fts_client):
    """TC-BR-FTS-012-03 [BR-FTS-012 archived-file-not-forwardable].

    Verify that an archived file cannot be forwarded.
    """
    f = create_file(
        subject="Archived Forward Test",
        comment_text="Init.",
        actor_user_id=101,
        actor_username="prof_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="prof_101",
        recipient_role="Professor",
    )
    archive_file(
        file_id=f.id,
        actor_user_id=101,
        actor_username="prof_101",
        actor_role="Professor",
    )
    res = fts_client(user_id=101).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={"to_user_id": 202, "to_username": "staff_202", "to_role": "Staff", "comment": "Forwarding archived."},
        format="json",
    )
    assert res.status_code == status.HTTP_409_CONFLICT


def test_tc_br_fts_012_04(fts_client):
    """TC-BR-FTS-012-04 [BR-FTS-012 archived-file-not-modifiable].

    Verify that an archived file cannot be modified (e.g., edited).
    """
    f = create_file(
        subject="Archived Edit Test",
        comment_text="Init.",
        actor_user_id=101,
        actor_username="prof_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="prof_101",
        recipient_role="Professor",
    )
    archive_file(
        file_id=f.id,
        actor_user_id=101,
        actor_username="prof_101",
        actor_role="Professor",
    )
    res = fts_client(user_id=101).put(
        f"/api/v1/fts/files/{f.id}/",
        data={"subject": "Modifying archived file."},
        format="json",
    )
    assert res.status_code == status.HTTP_409_CONFLICT


def test_tc_br_fts_013_01(fts_client):
    """TC-BR-FTS-013-01 [BR-FTS-013 notification-triggered-on-file-received].

    Verify that FTS triggers a notification event when a file is received by a user.
    """
    f = create_file(
        subject="Notify Received Test",
        comment_text="Init.",
        actor_user_id=101,
        actor_username="prof_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="prof_101",
        recipient_role="Professor",
    )
    fts_client(user_id=101).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={"to_user_id": 202, "to_username": "staff_202", "to_role": "Staff", "comment": "Fwd to 202."},
        format="json",
    )
    assert NotificationEvent.objects.filter(recipient_user_id=202, event_type="FILE_FORWARDED").exists()


def test_tc_br_fts_013_02(fts_client):
    """TC-BR-FTS-013-02 [BR-FTS-013 notification-triggered-on-file-archived].

    Verify that FTS triggers a notification event when a file is archived.
    """
    f = create_file(
        subject="Notify Archive Test",
        comment_text="Init.",
        actor_user_id=101,
        actor_username="prof_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="prof_101",
        recipient_role="Professor",
    )
    fts_client(user_id=101).post(f"/api/v1/fts/files/{f.id}/archive/")
    assert NotificationEvent.objects.filter(recipient_user_id=101, event_type="FILE_ARCHIVED").exists()


def test_tc_br_fts_014_01(stub_iam):
    """TC-BR-FTS-014-01 [BR-FTS-014 integration-api-enforces-fts-rbac].

    Verify that when a consuming Fusion module invokes an FTS integration API,
    FTS enforces its own RBAC and audit rules.
    """
    stub_iam(
        make_fts_session(
            user_id=500,
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
            "comment": "Leave approval file integration.",
            "is_draft": False,
            "recipient_user_id": 202,
            "recipient_username": "staff_202",
            "recipient_role": "Junior Superintendent",
        },
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()
    assert FileAuditLog.objects.filter(file_id=data["id"]).exists()


def test_tc_br_fts_014_02(stub_iam):
    """TC-BR-FTS-014-02 [BR-FTS-014 integration-api-rejects-unauthorized-request].

    Verify that the FTS integration API rejects requests that do not satisfy FTS authorization rules.
    """
    stub_iam(
        make_fts_session(
            user_id=500,
            kind="faculty",
            permissions=(),  # No integration permission
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token integ-unauth-token")

    res = c.post(
        "/api/v1/fts/integrations/requests/",
        data={
            "subject": "Unauthorized Integration Request",
            "comment": "Attempting without grant.",
            "is_draft": False,
        },
        format="json",
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN
