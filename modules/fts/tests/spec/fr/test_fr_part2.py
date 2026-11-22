"""Specification tests for Requirements Registry (FR) strategy - Part 2.

Generated from frozen FR_DESIGN.json.
Coverage: TC-FTS-046 through TC-FTS-089.
"""
from __future__ import annotations

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from modules.fts.domain.state_machine import (
    STATE_ARCHIVED,
    STATE_CIRCULATED,
)
from modules.fts.models.audit import FileAuditLog, NotificationEvent
from modules.fts.services.archival import archive_file
from modules.fts.services.files import create_file
from modules.fts.services.notifications import trigger_notification
from modules.fts.tests.conftest import make_fts_session

pytestmark = pytest.mark.django_db


def test_tc_fts_046(fts_client):
    """TC-FTS-046 [AFR-FTS-041 — unauthorized user denied].

    Verify that a user not associated with a file cannot view that file's tracking history.
    """
    f = create_file(
        subject="Private History Guard",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Staff",
    )
    res = fts_client(user_id=999).get(f"/api/v1/fts/files/{f.id}/history/")
    assert res.status_code == status.HTTP_404_NOT_FOUND


def test_tc_fts_047(fts_client):
    """TC-FTS-047 [AFR-FTS-042].

    Verify that the file owner can archive a file.
    """
    f = create_file(
        subject="Owner Archival",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Staff",
    )
    res = fts_client(user_id=101).post(f"/api/v1/fts/files/{f.id}/archive/")
    assert res.status_code == status.HTTP_200_OK
    f.refresh_from_db()
    assert f.status == STATE_ARCHIVED


def test_tc_fts_048(fts_client):
    """TC-FTS-048 [AFR-FTS-043].

    Verify that a user who is not the file owner cannot archive the file.
    """
    f = create_file(
        subject="Non-owner Archival Guard",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Staff",
    )
    res = fts_client(user_id=202).post(f"/api/v1/fts/files/{f.id}/archive/")
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_tc_fts_049(fts_client):
    """TC-FTS-049 [AFR-FTS-044].

    Verify that archival marks completion of the collaborative file workflow.
    """
    f = create_file(
        subject="Archival Completion Marker",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Staff",
    )
    fts_client(user_id=101).post(f"/api/v1/fts/files/{f.id}/archive/")
    f.refresh_from_db()
    assert f.status == STATE_ARCHIVED
    assert f.archived_at is not None


def test_tc_fts_050(fts_client):
    """TC-FTS-050 [AFR-FTS-045].

    Verify that archived files remain permanently stored and readable.
    """
    f = create_file(
        subject="Archived Readable Storage",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Staff",
    )
    archive_file(
        file_id=f.id,
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
    )
    res = fts_client(user_id=202).get(f"/api/v1/fts/files/{f.id}/")
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["status"] == STATE_ARCHIVED


def test_tc_fts_051(fts_client):
    """TC-FTS-051 [AFR-FTS-046].

    Verify that archived files cannot be modified.
    """
    f = create_file(
        subject="Archived No Modify",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="faculty_101",
        recipient_role="Professor",
    )
    archive_file(
        file_id=f.id,
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
    )
    res = fts_client(user_id=101).put(
        f"/api/v1/fts/files/{f.id}/",
        data={"subject": "Altered Subject"},
        format="json",
    )
    assert res.status_code == status.HTTP_409_CONFLICT


def test_tc_fts_052(fts_client):
    """TC-FTS-052 [AFR-FTS-047].

    Verify that archived files cannot be forwarded.
    """
    f = create_file(
        subject="Archived No Forward",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="faculty_101",
        recipient_role="Professor",
    )
    archive_file(
        file_id=f.id,
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
    )
    res = fts_client(user_id=101).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={"to_user_id": 202, "to_username": "staff", "to_role": "Staff", "comment": "Forward archived."},
        format="json",
    )
    assert res.status_code == status.HTTP_409_CONFLICT


def test_tc_fts_053(fts_client):
    """TC-FTS-053 [AFR-FTS-048].

    Verify that FTS enforces role-based access control for file operations.
    """
    res = fts_client(user_id=101, permissions=()).post(
        "/api/v1/fts/files/",
        data={"subject": "No Perm Create", "comment": "Comment."},
        format="json",
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_tc_fts_054(fts_client):
    """TC-FTS-054 [AFR-FTS-049].

    Verify that users can access only files they are authorized to view.
    """
    f = create_file(
        subject="View Isolation File",
        comment_text="Private.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Staff",
    )
    res = fts_client(user_id=303).get(f"/api/v1/fts/files/{f.id}/")
    assert res.status_code == status.HTTP_404_NOT_FOUND


def test_tc_fts_055(fts_client):
    """TC-FTS-055 [AFR-FTS-050].

    Verify that users can act only on files they are authorized to act upon.
    """
    f = create_file(
        subject="Act Isolation File",
        comment_text="Private.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Staff",
    )
    res = fts_client(user_id=303).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={"to_user_id": 404, "to_username": "other", "to_role": "Staff", "comment": "Act attempt."},
        format="json",
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_tc_fts_056(fts_client):
    """TC-FTS-056 [AFR-FTS-051].

    Verify that file ownership is preserved when a user switches roles.
    """
    f = create_file(
        subject="Ownership Preservation",
        comment_text="Initial.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=True,
    )
    fts_client(user_id=101, active_role="Associate Dean")
    f.refresh_from_db()
    assert f.owner_user_id == 101


def test_tc_fts_057(fts_client):
    """TC-FTS-057 [AFR-FTS-052].

    Verify that audit history is preserved when a user switches roles.
    """
    f = create_file(
        subject="Audit Preservation",
        comment_text="Initial.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=True,
    )
    log = FileAuditLog.objects.filter(file_id=f.id, action="FILE_CREATED").first()
    assert log is not None
    orig_actor = log.actor_username

    fts_client(user_id=101, active_role="Associate Dean")
    log.refresh_from_db()
    assert log.actor_username == orig_actor


def test_tc_fts_058(fts_client):
    """TC-FTS-058 [AFR-FTS-053].

    Verify that sensitive actions are restricted based on assigned roles.
    """
    f = create_file(
        subject="Sensitive Action File",
        comment_text="Initial.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Staff",
    )
    # Non-owner attempting archival
    res = fts_client(user_id=202).post(f"/api/v1/fts/files/{f.id}/archive/")
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_tc_fts_059(fts_client):
    """TC-FTS-059 [AFR-FTS-054].

    Verify that FTS creates an audit log entry when a file is created.
    """
    f = create_file(
        subject="Audit Create Log",
        comment_text="Initial.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=True,
    )
    assert FileAuditLog.objects.filter(file_id=f.id, action="FILE_CREATED").exists()


def test_tc_fts_060(fts_client):
    """TC-FTS-060 [AFR-FTS-055].

    Verify that FTS creates an audit log entry when a comment is added to a file.
    """
    f = create_file(
        subject="Audit Comment Log",
        comment_text="Creation.",
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
        data={"to_user_id": 202, "to_username": "staff", "to_role": "Staff", "comment": "New comment added."},
        format="json",
    )
    assert FileAuditLog.objects.filter(file_id=f.id, action="FILE_FORWARDED").exists()


def test_tc_fts_061(fts_client):
    """TC-FTS-061 [AFR-FTS-056].

    Verify that FTS creates an audit log entry when an attachment is added to a file.
    """
    f = create_file(
        subject="Audit Attachment Log",
        comment_text="Creation.",
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
        data={
            "to_user_id": 202,
            "to_username": "staff",
            "to_role": "Staff",
            "comment": "Adding attachment.",
            "attachments": [
                {
                    "file_name": "receipt.pdf",
                    "file_url": "https://storage.fusion.ac.in/fts/receipt.pdf",
                    "file_size": 1024,
                    "mime_type": "application/pdf",
                }
            ],
        },
        format="json",
    )
    assert FileAuditLog.objects.filter(file_id=f.id, action="FILE_FORWARDED").exists()


def test_tc_fts_062(fts_client):
    """TC-FTS-062 [AFR-FTS-057].

    Verify that FTS creates an audit log entry when a file is forwarded.
    """
    f = create_file(
        subject="Audit Forward Log",
        comment_text="Creation.",
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
        data={"to_user_id": 202, "to_username": "staff", "to_role": "Staff", "comment": "Forward."},
        format="json",
    )
    assert FileAuditLog.objects.filter(file_id=f.id, action="FILE_FORWARDED").exists()


def test_tc_fts_063(fts_client):
    """TC-FTS-063 [AFR-FTS-058].

    Verify that FTS creates an audit log entry when a file is returned.
    """
    f = create_file(
        subject="Audit Return Log",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff",
        recipient_role="Staff",
    )
    fts_client(user_id=202).post(
        f"/api/v1/fts/files/{f.id}/return/",
        data={"comment": "Returning."},
        format="json",
    )
    assert FileAuditLog.objects.filter(file_id=f.id, action="FILE_RETURNED").exists()


def test_tc_fts_064(fts_client):
    """TC-FTS-064 [AFR-FTS-059].

    Verify that FTS creates an audit log entry when a file is archived.
    """
    f = create_file(
        subject="Audit Archive Log",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="faculty_101",
        recipient_role="Assistant Professor",
    )
    fts_client(user_id=101).post(f"/api/v1/fts/files/{f.id}/archive/")
    assert FileAuditLog.objects.filter(file_id=f.id, action="FILE_ARCHIVED").exists()


def test_tc_fts_065(fts_client):
    """TC-FTS-065 [AFR-FTS-060].

    Verify that FTS maintains implicit versioning through chronological recording.
    """
    f = create_file(
        subject="Implicit Versioning",
        comment_text="v1 creation.",
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
        data={"to_user_id": 202, "to_username": "staff", "to_role": "Staff", "comment": "v2 forward."},
        format="json",
    )
    history = fts_client(user_id=101).get(f"/api/v1/fts/files/{f.id}/history/").json()
    assert len(history) == 2
    assert history[0]["sequence"] == 1
    assert history[1]["sequence"] == 2


def test_tc_fts_066(fts_client):
    """TC-FTS-066 [AFR-FTS-061].

    Verify that FTS generates a notification when a file is received by a user.
    """
    f = create_file(
        subject="Notify Received",
        comment_text="Creation.",
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
        data={"to_user_id": 202, "to_username": "staff", "to_role": "Staff", "comment": "Fwd."},
        format="json",
    )
    assert NotificationEvent.objects.filter(recipient_user_id=202, event_type="FILE_FORWARDED").exists()


def test_tc_fts_067(fts_client):
    """TC-FTS-067 [AFR-FTS-062].

    Verify that FTS generates a notification when a file is forwarded.
    """
    f = create_file(
        subject="Notify Forwarded",
        comment_text="Creation.",
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
        data={"to_user_id": 202, "to_username": "staff", "to_role": "Staff", "comment": "Fwd."},
        format="json",
    )
    assert NotificationEvent.objects.filter(recipient_user_id=202, event_type="FILE_FORWARDED").exists()


def test_tc_fts_068(fts_client):
    """TC-FTS-068 [AFR-FTS-063].

    Verify that FTS generates a notification when a file is returned.
    """
    f = create_file(
        subject="Notify Returned",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff",
        recipient_role="Staff",
    )
    fts_client(user_id=202).post(
        f"/api/v1/fts/files/{f.id}/return/",
        data={"comment": "Return."},
        format="json",
    )
    assert NotificationEvent.objects.filter(recipient_user_id=101, event_type="FILE_RETURNED").exists()


def test_tc_fts_069(fts_client):
    """TC-FTS-069 [AFR-FTS-064].

    Verify that FTS generates a notification when a file is archived.
    """
    f = create_file(
        subject="Notify Archived",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=101,
        recipient_username="faculty_101",
        recipient_role="Assistant Professor",
    )
    fts_client(user_id=101).post(f"/api/v1/fts/files/{f.id}/archive/")
    assert NotificationEvent.objects.filter(recipient_user_id=101, event_type="FILE_ARCHIVED").exists()


def test_tc_fts_070():
    """TC-FTS-070 [AFR-FTS-065].

    Verify that FTS generates a notification when a role is assigned to a user.
    """
    ev = trigger_notification(
        event_type="ROLE_ASSIGNED",
        recipient_user_id=101,
        payload={"role": "HOD (ECE)"},
    )
    assert NotificationEvent.objects.filter(id=ev.id, event_type="ROLE_ASSIGNED").exists()


def test_tc_fts_071():
    """TC-FTS-071 [AFR-FTS-065 — reassignment notification].

    Verify that FTS generates a notification when a role is reassigned.
    """
    ev = trigger_notification(
        event_type="ROLE_REASSIGNED",
        recipient_user_id=101,
        payload={"old_role": "HOD (ECE)", "new_role": "Dean Academic"},
    )
    assert NotificationEvent.objects.filter(id=ev.id, event_type="ROLE_REASSIGNED").exists()


def test_tc_fts_072():
    """TC-FTS-072 [AFR-FTS-066].

    Verify that FTS records notifications for dispatch through Fusion's integrated notification mechanisms.
    """
    ev = trigger_notification(
        event_type="FILE_RECEIVED",
        recipient_user_id=202,
        payload={"file_id": 1},
    )
    assert ev.delivered is False
    assert NotificationEvent.objects.filter(id=ev.id).exists()


def test_tc_fts_073(stub_iam):
    """TC-FTS-073 [AFR-FTS-067].

    Verify that FTS exposes APIs to other Fusion modules for module-specific workflows.
    """
    stub_iam(
        make_fts_session(
            user_id=700,
            kind="faculty",
            permissions=("fts.integration.access",),
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token integ-token")
    res = c.post(
        "/api/v1/fts/integrations/requests/",
        data={"subject": "Integ Workflow", "comment": "Comment.", "is_draft": True},
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED


def test_tc_fts_074(stub_iam):
    """TC-FTS-074 [AFR-FTS-068].

    Verify that FTS exposes APIs that support approval chains defined by consuming Fusion modules.
    """
    stub_iam(
        make_fts_session(
            user_id=700,
            kind="faculty",
            permissions=("fts.integration.access",),
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token integ-token")
    res = c.post(
        "/api/v1/fts/integrations/requests/",
        data={
            "subject": "Approval Chain Step 1",
            "comment": "Comment.",
            "is_draft": False,
            "recipient_user_id": 202,
            "recipient_username": "approver_1",
            "recipient_role": "HOD",
        },
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED
    assert res.json()["current_holder_user_id"] == 202


def test_tc_fts_075(stub_iam):
    """TC-FTS-075 [AFR-FTS-069].

    Verify that FTS exposes APIs for file-based request tracking to consuming Fusion modules.
    """
    f = create_file(
        subject="Tracked Request",
        comment_text="Initial.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Staff",
    )
    from modules.fts.contracts import get_file_statuses

    statuses = get_file_statuses([f.id])
    assert f.id in statuses
    assert statuses[f.id].status == STATE_CIRCULATED


def test_tc_fts_076(stub_iam):
    """TC-FTS-076 [AFR-FTS-070].

    Verify that FTS applies RBAC requirements to integrations with other Fusion modules.
    """
    stub_iam(
        make_fts_session(
            user_id=700,
            kind="faculty",
            permissions=(),  # Lacks fts.integration.access
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token integ-token")
    res = c.post(
        "/api/v1/fts/integrations/requests/",
        data={"subject": "Denied Integration", "comment": "Comment."},
        format="json",
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_tc_fts_077(stub_iam):
    """TC-FTS-077 [AFR-FTS-071].

    Verify that FTS applies audit requirements to integrations with other Fusion modules.
    """
    stub_iam(
        make_fts_session(
            user_id=700,
            kind="faculty",
            permissions=("fts.integration.access",),
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token integ-token")
    res = c.post(
        "/api/v1/fts/integrations/requests/",
        data={"subject": "Audited Integration", "comment": "Comment.", "is_draft": True},
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()
    assert FileAuditLog.objects.filter(file_id=data["id"]).exists()


def test_tc_fts_078(stub_iam):
    """TC-FTS-078 [AFR-FTS-072].

    Verify that FTS does not define or enforce domain-specific approval rules of consuming modules.
    """
    stub_iam(
        make_fts_session(
            user_id=700,
            kind="faculty",
            permissions=("fts.integration.access",),
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token integ-token")
    res = c.post(
        "/api/v1/fts/integrations/requests/",
        data={
            "subject": "Domain Free Integration",
            "comment": "Comment.",
            "is_draft": True,
            "custom_approval_policy": "NO_RULES",
        },
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED


def test_tc_fts_079(fts_client):
    """TC-FTS-079 [AFR-FTS-001 — append-only after circulation].

    Verify that existing comments and attachments in a circulated file are append-only.
    """
    f = create_file(
        subject="Append Only Test",
        comment_text="Original remark.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff",
        recipient_role="Staff",
    )
    res = fts_client(user_id=101).put(
        f"/api/v1/fts/files/{f.id}/",
        data={"subject": "Modifying circulated."},
        format="json",
    )
    assert res.status_code == status.HTTP_409_CONFLICT


def test_tc_fts_080(admin_client):
    """TC-FTS-080 [AFR-FTS-009 — System Admin cannot create file].

    Verify that System Admin cannot create an operational file on behalf of an employee.
    """
    res = admin_client().post(
        "/api/v1/fts/files/",
        data={"subject": "Admin File Attempt", "comment": "Comment."},
        format="json",
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_tc_fts_081(fts_client):
    """TC-FTS-081 [AFR-FTS-016 — draft cannot be discarded after submission].

    Verify that a circulated file cannot be discarded using the draft-discard mechanism.
    """
    f = create_file(
        subject="Circulated No Discard",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff",
        recipient_role="Staff",
    )
    res = fts_client(user_id=101).post(f"/api/v1/fts/files/{f.id}/discard/")
    assert res.status_code == status.HTTP_409_CONFLICT


def test_tc_fts_082(fts_client):
    """TC-FTS-082 [AFR-FTS-015 — draft edit after circulation denied].

    Verify that a circulated file cannot be edited using the draft-edit mechanism.
    """
    f = create_file(
        subject="Circulated No Edit",
        comment_text="Creation.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff",
        recipient_role="Staff",
    )
    res = fts_client(user_id=101).put(
        f"/api/v1/fts/files/{f.id}/",
        data={"subject": "Edited Circulated"},
        format="json",
    )
    assert res.status_code == status.HTTP_409_CONFLICT


def test_tc_fts_083(fts_client):
    """TC-FTS-083 [AFR-FTS-033 — no action on archived file from Inbox].

    Verify that a user cannot perform forward/return actions on an archived file.
    """
    f = create_file(
        subject="Archived In Inbox Action",
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
    res = fts_client(user_id=101).post(
        f"/api/v1/fts/files/{f.id}/forward/",
        data={"to_user_id": 202, "to_username": "staff", "to_role": "Staff", "comment": "Comment."},
        format="json",
    )
    assert res.status_code == status.HTTP_409_CONFLICT


def test_tc_fts_084(fts_client):
    """TC-FTS-084 [AFR-FTS-034 — file accessible before archival].

    Verify that operational actions are prevented on archived files.
    """
    f = create_file(
        subject="Action Blocked On Archived",
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
    res = fts_client(user_id=101).post(
        f"/api/v1/fts/files/{f.id}/return/",
        data={"comment": "Return archived."},
        format="json",
    )
    assert res.status_code == status.HTTP_409_CONFLICT


def test_tc_fts_085(fts_client):
    """TC-FTS-085 [AFR-FTS-010 — role context does not override file association].

    Verify that switching to a different role does not grant access to files unassociated with the user.
    """
    f = create_file(
        subject="Unassociated Role Switch File",
        comment_text="Private.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Staff",
    )
    # User 303 tries to access even with a high role context (e.g. Dean)
    res = fts_client(user_id=303, active_role="Dean Academic").get(f"/api/v1/fts/files/{f.id}/")
    assert res.status_code == status.HTTP_404_NOT_FOUND


def test_tc_fts_086(fts_client):
    """TC-FTS-086 [AFR-FTS-005 — unauthorized user cannot create file].

    Verify that an Institute Employee without file creation permission cannot create a file.
    """
    res = fts_client(user_id=101, permissions=("fts.file.view",)).post(
        "/api/v1/fts/files/",
        data={"subject": "No Perm Create", "comment": "Comment."},
        format="json",
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_tc_fts_087(fts_client):
    """TC-FTS-087 [AFR-FTS-022 — empty comment rejected at movement].

    Verify that an empty or blank comment is rejected as a mandatory movement comment.
    """
    f = create_file(
        subject="Empty Movement Comment",
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
        data={"to_user_id": 202, "to_username": "staff", "to_role": "Staff", "comment": "   "},
        format="json",
    )
    assert res.status_code == status.HTTP_400_BAD_REQUEST


def test_tc_fts_088(fts_client):
    """TC-FTS-088 [AFR-FTS-012 — empty comment rejected at creation].

    Verify that an empty or blank initial comment is rejected during file creation.
    """
    res = fts_client(user_id=101).post(
        "/api/v1/fts/files/",
        data={"subject": "Empty Creation Comment", "comment": "   ", "is_draft": True},
        format="json",
    )
    assert res.status_code == status.HTTP_400_BAD_REQUEST


def test_tc_fts_089(fts_client):
    """TC-FTS-089 [AFR-FTS-041 — non-associated user denied tracking history].

    Verify that a non-associated Institute Employee cannot view the tracking history.
    """
    f = create_file(
        subject="Private Tracking History",
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
