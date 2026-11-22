"""Specification tests for Workflows (WF) strategy.

Generated from frozen WF_DESIGN.json.
Coverage: BW-FTS-01..08, CW-FTS-01..02.
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
from modules.fts.models.audit import FileAuditLog, NotificationEvent
from modules.fts.models.files import File
from modules.fts.services.archival import archive_file
from modules.fts.services.files import create_file

pytestmark = pytest.mark.django_db


def test_tc_wf_001(fts_client):
    """TC-WF-001 [BW-FTS-01 forward-authorized-path].

    Verify that an authorized current holder can forward an active file to a
    valid recipient with a mandatory comment, resulting in the file being held
    by the recipient.
    """
    fts_client(user_id=101, kind="faculty", active_role="Assistant Professor")

    f = create_file(
        subject="WF-001 File",
        comment_text="Initial comment.",
        actor_user_id=101,
        actor_username="emp_a",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="emp_a",
        recipient_role="Assistant Professor",
    )

    res = fts_client(user_id=101).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={
            "to_user_id": 202,
            "to_username": "emp_b",
            "to_role": "Junior Superintendent",
            "comment": "Forwarding to Employee B.",
        },
        format="json",
    )
    assert res.status_code == status.HTTP_200_OK

    f.refresh_from_db()
    assert f.status == STATE_CIRCULATED
    assert f.current_holder_user_id == 202

    inbox_b = fts_client(user_id=202).get("/api/v1/fts/inbox/").json()
    assert any(item["id"] == f.id for item in inbox_b)
    assert NotificationEvent.objects.filter(recipient_user_id=202, event_type="FILE_FORWARDED").exists()


def test_tc_wf_002(fts_client):
    """TC-WF-002 [BW-FTS-01 guard-no-comment].

    Verify that forwarding is rejected when no mandatory movement comment is provided.
    """
    fts_client(user_id=101)
    f = create_file(
        subject="WF-002 File",
        comment_text="Initial comment.",
        actor_user_id=101,
        actor_username="emp_a",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="emp_a",
        recipient_role="Assistant Professor",
    )

    res = fts_client(user_id=101).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={
            "to_user_id": 202,
            "to_username": "emp_b",
            "to_role": "Junior Superintendent",
            "comment": "   ",
        },
        format="json",
    )
    assert res.status_code == status.HTTP_400_BAD_REQUEST

    f.refresh_from_db()
    assert f.current_holder_user_id == 101


def test_tc_wf_003(fts_client):
    """TC-WF-003 [BW-FTS-01 guard-archived-file].

    Verify that forwarding is rejected when the file is already archived.
    """
    fts_client(user_id=101)
    f = create_file(
        subject="WF-003 File",
        comment_text="Initial comment.",
        actor_user_id=101,
        actor_username="emp_a",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="emp_a",
        recipient_role="Assistant Professor",
    )
    archive_file(
        file_id=f.id,
        actor_user_id=101,
        actor_username="emp_a",
        actor_role="Assistant Professor",
    )

    res = fts_client(user_id=101).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={
            "to_user_id": 202,
            "to_username": "emp_b",
            "to_role": "Junior Superintendent",
            "comment": "Attempt forwarding archived file.",
        },
        format="json",
    )
    assert res.status_code == status.HTTP_409_CONFLICT
    f.refresh_from_db()
    assert f.status == STATE_ARCHIVED


def test_tc_wf_004(fts_client):
    """TC-WF-004 [BW-FTS-01 guard-unauthorized-sender].

    Verify that an unauthorized user cannot forward a file.
    """
    c_c = fts_client(user_id=303, kind="faculty", active_role="Associate Professor")
    f = create_file(
        subject="WF-004 File",
        comment_text="Initial comment.",
        actor_user_id=101,
        actor_username="emp_a",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="emp_b",
        recipient_role="Junior Superintendent",
    )

    res = c_c.post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={
            "to_user_id": 404,
            "to_username": "emp_d",
            "to_role": "Staff",
            "comment": "Unauthorized forward attempt.",
        },
        format="json",
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_tc_wf_005(fts_client):
    """TC-WF-005 [BW-FTS-02 onward-forwarding-one-loop].

    Verify that a current holder of an active circulated file can forward it
    onward to a next recipient with a mandatory comment, completing one loop
    traversal.
    """

    f = create_file(
        subject="WF-005 File",
        comment_text="Initial circulation.",
        actor_user_id=101,
        actor_username="emp_a",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="emp_b",
        recipient_role="Junior Superintendent",
    )

    res = fts_client(user_id=202, kind='staff', active_role='Junior Superintendent').post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={
            "to_user_id": 303,
            "to_username": "emp_c",
            "to_role": "Dean Academic",
            "comment": "Onward forwarding to Dean.",
        },
        format="json",
    )
    assert res.status_code == status.HTTP_200_OK

    f.refresh_from_db()
    assert f.status == STATE_CIRCULATED
    assert f.current_holder_user_id == 303

    inbox_c = fts_client(user_id=303, kind='faculty', active_role='Dean Academic').get("/api/v1/fts/inbox/").json()
    assert any(item["id"] == f.id for item in inbox_c)


def test_tc_wf_006(fts_client):
    """TC-WF-006 [BW-FTS-02 guard-no-comment].

    Verify that onward forwarding is rejected when mandatory movement comment is absent.
    """
    fts_client(user_id=202)
    f = create_file(
        subject="WF-006 File",
        comment_text="Initial comment.",
        actor_user_id=101,
        actor_username="emp_a",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="emp_b",
        recipient_role="Junior Superintendent",
    )

    res = fts_client(user_id=202, kind='staff', active_role='Junior Superintendent').post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={
            "to_user_id": 303,
            "to_username": "emp_c",
            "to_role": "Dean Academic",
            "comment": "",
        },
        format="json",
    )
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    f.refresh_from_db()
    assert f.current_holder_user_id == 202


def test_tc_wf_007(fts_client):
    """TC-WF-007 [BW-FTS-03 return-authorized-path].

    Verify that an authorized current recipient can return an active file to the
    previous sender with a mandatory comment.
    """
    fts_client(user_id=202)
    f = create_file(
        subject="WF-007 File",
        comment_text="Initial comment from A to B.",
        actor_user_id=101,
        actor_username="emp_a",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="emp_b",
        recipient_role="Junior Superintendent",
    )

    res = fts_client(user_id=202, kind='staff', active_role='Junior Superintendent').post(
        f"/api/v1/fts/files/{f.id}/return/",
        data={"comment": "Returning file to Employee A for clarification."},
        format="json",
    )
    assert res.status_code == status.HTTP_200_OK

    f.refresh_from_db()
    assert f.status == STATE_CIRCULATED
    assert f.current_holder_user_id == 101
    assert NotificationEvent.objects.filter(recipient_user_id=101, event_type="FILE_RETURNED").exists()


def test_tc_wf_008(fts_client):
    """TC-WF-008 [BW-FTS-03 guard-no-comment].

    Verify that the return action is rejected when no mandatory movement comment is provided.
    """
    fts_client(user_id=202)
    f = create_file(
        subject="WF-008 File",
        comment_text="Initial comment.",
        actor_user_id=101,
        actor_username="emp_a",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="emp_b",
        recipient_role="Junior Superintendent",
    )

    res = fts_client(user_id=202, kind='staff', active_role='Junior Superintendent').post(
        f"/api/v1/fts/files/{f.id}/return/",
        data={"comment": "    "},
        format="json",
    )
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    f.refresh_from_db()
    assert f.current_holder_user_id == 202


def test_tc_wf_009(fts_client):
    """TC-WF-009 [BW-FTS-03 guard-unauthorized-recipient].

    Verify that an unauthorized user cannot return a file.
    """
    c_d = fts_client(user_id=404)
    f = create_file(
        subject="WF-009 File",
        comment_text="Initial comment.",
        actor_user_id=101,
        actor_username="emp_a",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="emp_b",
        recipient_role="Junior Superintendent",
    )

    res = c_d.post(
        f"/api/v1/fts/files/{f.id}/return/",
        data={"comment": "Unauthorized return attempt."},
        format="json",
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_tc_wf_010(fts_client):
    """TC-WF-010 [BW-FTS-04 archive-owner-path].

    Verify that the file owner can archive a completed active/circulated file,
    closing the lifecycle.
    """
    fts_client(user_id=101)
    f = create_file(
        subject="WF-010 File",
        comment_text="Initial comment.",
        actor_user_id=101,
        actor_username="emp_a",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="emp_b",
        recipient_role="Junior Superintendent",
    )

    res = fts_client(user_id=101).post(f"/api/v1/fts/files/{f.id}/archive/")
    assert res.status_code == status.HTTP_200_OK

    f.refresh_from_db()
    assert f.status == STATE_ARCHIVED
    assert f.archived_at is not None
    assert NotificationEvent.objects.filter(recipient_user_id=101, event_type="FILE_ARCHIVED").exists()


def test_tc_wf_011(fts_client):
    """TC-WF-011 [BW-FTS-04 guard-non-owner-cannot-archive].

    Verify that a non-owner cannot archive a file.
    """
    fts_client(user_id=202)
    f = create_file(
        subject="WF-011 File",
        comment_text="Initial comment.",
        actor_user_id=101,
        actor_username="emp_a",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="emp_b",
        recipient_role="Junior Superintendent",
    )

    res = fts_client(user_id=202, kind='staff', active_role='Junior Superintendent').post(f"/api/v1/fts/files/{f.id}/archive/")
    assert res.status_code == status.HTTP_403_FORBIDDEN

    f.refresh_from_db()
    assert f.status == STATE_CIRCULATED


def test_tc_wf_012(fts_client):
    """TC-WF-012 [BW-FTS-04 guard-already-archived].

    Verify that archiving an already-archived file is rejected.
    """
    fts_client(user_id=101)
    f = create_file(
        subject="WF-012 File",
        comment_text="Initial comment.",
        actor_user_id=101,
        actor_username="emp_a",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="emp_a",
        recipient_role="Assistant Professor",
    )
    archive_file(
        file_id=f.id,
        actor_user_id=101,
        actor_username="emp_a",
        actor_role="Assistant Professor",
    )

    res = fts_client(user_id=101).post(f"/api/v1/fts/files/{f.id}/archive/")
    assert res.status_code == status.HTTP_409_CONFLICT


def test_tc_wf_013(fts_client):
    """TC-WF-013 [BW-FTS-04 guard-cannot-archive-draft].

    Verify that a draft (uncirculated) file cannot be archived.
    """
    fts_client(user_id=101)
    f = create_file(
        subject="WF-013 Draft",
        comment_text="Draft comment.",
        actor_user_id=101,
        actor_username="emp_a",
        actor_role="Assistant Professor",
        is_draft=True,
    )

    res = fts_client(user_id=101).post(f"/api/v1/fts/files/{f.id}/archive/")
    assert res.status_code == status.HTTP_409_CONFLICT
    f.refresh_from_db()
    assert f.status == STATE_DRAFT


def test_tc_wf_014(fts_client):
    """TC-WF-014 [BW-FTS-05 create-and-circulate-zero-draft-edit].

    Verify creation followed directly by initial circulation with zero draft-edit traversal.
    """
    c_a = fts_client(user_id=101)
    res_create = c_a.post(
        "/api/v1/fts/files/",
        data={
            "subject": "WF-014 Requisition",
            "comment": "Initial mandatory comment.",
            "is_draft": True,
        },
        format="json",
    )
    assert res_create.status_code == status.HTTP_201_CREATED
    file_id = res_create.json()["id"]

    res_fwd = c_a.post(
        f"/api/v1/fts/files/{file_id}/forward/",
        data={
            "to_user_id": 202,
            "to_username": "emp_b",
            "to_role": "Junior Superintendent",
            "comment": "Submitting draft for review without prior edit.",
        },
        format="json",
    )
    assert res_fwd.status_code == status.HTTP_200_OK

    f = File.objects.get(id=file_id)
    assert f.status == STATE_CIRCULATED
    assert f.current_holder_user_id == 202


def test_tc_wf_015(fts_client):
    """TC-WF-015 [BW-FTS-05 guard-no-comment-creation].

    Verify that file creation is rejected when the mandatory initial comment is missing.
    """
    fts_client(user_id=101)
    res = fts_client(user_id=101).post(
        "/api/v1/fts/files/",
        data={"subject": "WF-015 File", "comment": "", "is_draft": True},
        format="json",
    )
    assert res.status_code == status.HTTP_400_BAD_REQUEST


def test_tc_wf_016(fts_client):
    """TC-WF-016 [BW-FTS-05 guard-no-comment-circulation].

    Verify that initial circulation from draft is rejected when mandatory movement comment is absent.
    """
    fts_client(user_id=101)
    f = create_file(
        subject="WF-016 File",
        comment_text="Initial comment.",
        actor_user_id=101,
        actor_username="emp_a",
        actor_role="Assistant Professor",
        is_draft=True,
    )

    res = fts_client(user_id=101).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={
            "to_user_id": 202,
            "to_username": "emp_b",
            "to_role": "Junior Superintendent",
            "comment": "",
        },
        format="json",
    )
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    f.refresh_from_db()
    assert f.status == STATE_DRAFT


def test_tc_wf_017(fts_client):
    """TC-WF-017 [BW-FTS-06 create-edit-once-circulate].

    Verify creation, exactly one draft-edit traversal, and subsequent initial circulation.
    """
    c_a = fts_client(user_id=101)
    res_create = c_a.post(
        "/api/v1/fts/files/",
        data={"subject": "WF-017 Initial Draft", "comment": "Initial comment.", "is_draft": True},
        format="json",
    )
    file_id = res_create.json()["id"]

    res_edit = c_a.put(
        f"/api/v1/fts/files/{file_id}/",
        data={"subject": "WF-017 Edited Draft", "comment": "Updated comment."},
        format="json",
    )
    assert res_edit.status_code == status.HTTP_200_OK
    assert res_edit.json()["subject"] == "WF-017 Edited Draft"

    res_fwd = c_a.post(
        f"/api/v1/fts/files/{file_id}/forward/",
        data={
            "to_user_id": 202,
            "to_username": "emp_b",
            "to_role": "Staff",
            "comment": "Circulating after one edit.",
        },
        format="json",
    )
    assert res_fwd.status_code == status.HTTP_200_OK
    f = File.objects.get(id=file_id)
    assert f.status == STATE_CIRCULATED


def test_tc_wf_018(fts_client):
    """TC-WF-018 [BW-FTS-06 guard-draft-edit-only-pre-circulation].

    Verify that draft editing is not permitted once the file has been circulated.
    """
    c_a = fts_client(user_id=101)
    f = create_file(
        subject="WF-018 Circulated",
        comment_text="Initial comment.",
        actor_user_id=101,
        actor_username="emp_a",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="emp_b",
        recipient_role="Junior Superintendent",
    )

    res = c_a.put(
        f"/api/v1/fts/files/{f.id}/",
        data={"subject": "Trying to edit circulated file."},
        format="json",
    )
    assert res.status_code == status.HTTP_409_CONFLICT


def test_tc_wf_019(fts_client):
    """TC-WF-019 [BW-FTS-07 create-and-discard-zero-edit].

    Verify creation followed by draft discard with zero draft-edit traversal.
    """
    c_a = fts_client(user_id=101)
    res_create = c_a.post(
        "/api/v1/fts/files/",
        data={"subject": "WF-019 Draft", "comment": "Draft comment.", "is_draft": True},
        format="json",
    )
    file_id = res_create.json()["id"]

    res_discard = c_a.post(f"/api/v1/fts/files/{file_id}/discard/")
    assert res_discard.status_code == status.HTTP_200_OK
    assert res_discard.json()["status"] == STATE_DISCARDED

    f = File.objects.get(id=file_id)
    assert f.status == STATE_DISCARDED

    # File no longer appears in active drafts
    drafts = c_a.get("/api/v1/fts/drafts/").json()
    assert not any(d["id"] == file_id for d in drafts)


def test_tc_wf_020(fts_client):
    """TC-WF-020 [BW-FTS-07 guard-discard-only-before-submission].

    Verify that discard is only available for draft files and not for circulated files.
    """
    fts_client(user_id=101)
    f = create_file(
        subject="WF-020 Circulated",
        comment_text="Initial comment.",
        actor_user_id=101,
        actor_username="emp_a",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="emp_b",
        recipient_role="Junior Superintendent",
    )

    res = fts_client(user_id=101).post(f"/api/v1/fts/files/{f.id}/discard/")
    assert res.status_code == status.HTTP_409_CONFLICT
    f.refresh_from_db()
    assert f.status == STATE_CIRCULATED


def test_tc_wf_021(fts_client):
    """TC-WF-021 [BW-FTS-08 edit-once-then-discard].

    Verify that a draft can be edited once and then discarded before circulation.
    """
    c_a = fts_client(user_id=101)
    res_create = c_a.post(
        "/api/v1/fts/files/",
        data={"subject": "WF-021 Draft", "comment": "Initial comment.", "is_draft": True},
        format="json",
    )
    file_id = res_create.json()["id"]

    res_edit = c_a.put(
        f"/api/v1/fts/files/{file_id}/",
        data={"subject": "WF-021 Updated Draft", "comment": "Updated comment."},
        format="json",
    )
    assert res_edit.status_code == status.HTTP_200_OK

    res_discard = c_a.post(f"/api/v1/fts/files/{file_id}/discard/")
    assert res_discard.status_code == status.HTTP_200_OK
    assert res_discard.json()["status"] == STATE_DISCARDED

    f = File.objects.get(id=file_id)
    assert f.status == STATE_DISCARDED


def test_tc_wf_022(fts_client):
    """TC-WF-022 [CW-FTS-01 forward-then-onward-forward-then-archive].

    Verify the composite collaborative lifecycle: initial forward (BW-FTS-01) ->
    onward forward (BW-FTS-02) -> archive (BW-FTS-04).
    """

    f = create_file(
        subject="CW-001 Lifecycle A",
        comment_text="Step 1 init.",
        actor_user_id=101,
        actor_username="emp_a",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="emp_a",
        recipient_role="Assistant Professor",
    )

    # Step 1: Forward A -> B
    res_fwd1 = fts_client(user_id=101).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={"to_user_id": 202, "to_username": "emp_b", "to_role": "Staff", "comment": "A forwards to B."},
        format="json",
    )
    assert res_fwd1.status_code == status.HTTP_200_OK

    # Step 2: Forward B -> C
    res_fwd2 = fts_client(user_id=202).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={"to_user_id": 303, "to_username": "emp_c", "to_role": "Dean", "comment": "B forwards to C."},
        format="json",
    )
    assert res_fwd2.status_code == status.HTTP_200_OK

    # Step 3: Owner A archives
    res_arch = fts_client(user_id=101).post(f"/api/v1/fts/files/{f.id}/archive/")
    assert res_arch.status_code == status.HTTP_200_OK
    f.refresh_from_db()
    assert f.status == STATE_ARCHIVED


def test_tc_wf_023(fts_client):
    """TC-WF-023 [CW-FTS-01 forward-then-return-then-archive].

    Verify the composite collaborative lifecycle: initial forward (BW-FTS-01) ->
    return (BW-FTS-03) -> archive (BW-FTS-04).
    """

    f = create_file(
        subject="CW-001 Lifecycle B",
        comment_text="Step 1 init.",
        actor_user_id=101,
        actor_username="emp_a",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="emp_a",
        recipient_role="Assistant Professor",
    )

    # Forward A -> B
    fts_client(user_id=101).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={"to_user_id": 202, "to_username": "emp_b", "to_role": "Staff", "comment": "To B."},
        format="json",
    )

    # Return B -> A
    res_ret = fts_client(user_id=202).post(
        f"/api/v1/fts/files/{f.id}/return/",
        data={"comment": "Returning to A."},
        format="json",
    )
    assert res_ret.status_code == status.HTTP_200_OK

    # Owner archives
    res_arch = fts_client(user_id=101).post(f"/api/v1/fts/files/{f.id}/archive/")
    assert res_arch.status_code == status.HTTP_200_OK
    f.refresh_from_db()
    assert f.status == STATE_ARCHIVED


def test_tc_wf_024(fts_client):
    """TC-WF-024 [CW-FTS-01 forward-onward-return-archive].

    Verify the composite path: initial forward -> onward forward -> return after onward traversal -> archive.
    """
    fts_client(user_id=303)

    f = create_file(
        subject="CW-001 Lifecycle C",
        comment_text="Step 1 init.",
        actor_user_id=101,
        actor_username="emp_a",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="emp_a",
        recipient_role="Assistant Professor",
    )

    # A -> B
    fts_client(user_id=101).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={"to_user_id": 202, "to_username": "emp_b", "to_role": "Staff", "comment": "A to B."},
        format="json",
    )
    # B -> C
    fts_client(user_id=202).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={"to_user_id": 303, "to_username": "emp_c", "to_role": "Dean", "comment": "B to C."},
        format="json",
    )
    # C -> B (return)
    res_ret = fts_client(user_id=303).post(
        f"/api/v1/fts/files/{f.id}/return/",
        data={"comment": "C returns to B."},
        format="json",
    )
    assert res_ret.status_code == status.HTTP_200_OK
    f.refresh_from_db()
    assert f.current_holder_user_id == 202

    # Owner A archives
    res_arch = fts_client(user_id=101).post(f"/api/v1/fts/files/{f.id}/archive/")
    assert res_arch.status_code == status.HTTP_200_OK
    f.refresh_from_db()
    assert f.status == STATE_ARCHIVED


def test_tc_wf_025(fts_client):
    """TC-WF-025 [CW-FTS-02 new-file-zero-draft-edit-circulate].

    Verify the composite new-file path: create -> circulate immediately (BW-FTS-05 integrated via CW-FTS-02).
    """
    fts_client(user_id=101)
    res = fts_client(user_id=101).post(
        "/api/v1/fts/files/",
        data={
            "subject": "CW-002 Immediate Circulate",
            "comment": "Initial mandatory comment.",
            "is_draft": False,
            "recipient_user_id": 202,
            "recipient_username": "emp_b",
            "recipient_role": "Staff",
        },
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()
    assert data["status"] == STATE_CIRCULATED
    assert data["current_holder_user_id"] == 202
    assert FileAuditLog.objects.filter(file_id=data["id"], action="FILE_CREATED").exists()


def test_tc_wf_026(fts_client):
    """TC-WF-026 [CW-FTS-02 new-file-one-draft-edit-then-circulate].

    Verify the composite new-file path: create -> edit draft once -> circulate (BW-FTS-06 integrated via CW-FTS-02).
    """
    c_a = fts_client(user_id=101)
    res_c = c_a.post(
        "/api/v1/fts/files/",
        data={"subject": "CW-002 Initial Draft", "comment": "Draft comment.", "is_draft": True},
        format="json",
    )
    file_id = res_c.json()["id"]

    c_a.put(
        f"/api/v1/fts/files/{file_id}/",
        data={"subject": "CW-002 Revised Draft", "comment": "Updated comment."},
        format="json",
    )

    res_fwd = c_a.post(
        f"/api/v1/fts/files/{file_id}/forward/",
        data={"to_user_id": 202, "to_username": "emp_b", "to_role": "Staff", "comment": "Circulate after edit."},
        format="json",
    )
    assert res_fwd.status_code == status.HTTP_200_OK
    f = File.objects.get(id=file_id)
    assert f.status == STATE_CIRCULATED
    assert f.current_holder_user_id == 202


def test_tc_wf_027(fts_client):
    """TC-WF-027 [CW-FTS-02 new-file-zero-draft-edit-discard].

    Verify the composite new-file path: create -> discard immediately with no prior edit (BW-FTS-07 integrated via CW-FTS-02).
    """
    c_a = fts_client(user_id=101)
    res_c = c_a.post(
        "/api/v1/fts/files/",
        data={"subject": "CW-027 Draft", "comment": "Draft comment.", "is_draft": True},
        format="json",
    )
    file_id = res_c.json()["id"]

    res_disc = c_a.post(f"/api/v1/fts/files/{file_id}/discard/")
    assert res_disc.status_code == status.HTTP_200_OK
    f = File.objects.get(id=file_id)
    assert f.status == STATE_DISCARDED


def test_tc_wf_028(fts_client):
    """TC-WF-028 [CW-FTS-02 new-file-one-draft-edit-then-discard].

    Verify the composite new-file path: create -> edit draft once -> discard (BW-FTS-08 integrated via CW-FTS-02).
    """
    c_a = fts_client(user_id=101)
    res_c = c_a.post(
        "/api/v1/fts/files/",
        data={"subject": "CW-028 Draft", "comment": "Draft comment.", "is_draft": True},
        format="json",
    )
    file_id = res_c.json()["id"]

    c_a.put(
        f"/api/v1/fts/files/{file_id}/",
        data={"subject": "CW-028 Updated Draft", "comment": "Updated comment."},
        format="json",
    )

    res_disc = c_a.post(f"/api/v1/fts/files/{file_id}/discard/")
    assert res_disc.status_code == status.HTTP_200_OK
    f = File.objects.get(id=file_id)
    assert f.status == STATE_DISCARDED
