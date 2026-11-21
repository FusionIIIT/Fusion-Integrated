"""API endpoint tests for FTS."""
import pytest
from rest_framework import status

from modules.fts.services.files import create_file

pytestmark = pytest.mark.django_db


def test_create_file_and_inbox_outbox(fts_client):
    c1 = fts_client(user_id=101, kind="faculty", active_role="Assistant Professor")
    c2 = fts_client(user_id=202, kind="staff", active_role="Junior Superintendent")

    payload = {
        "subject": "Lab Equipment Requisition",
        "description": "40 monitors needed.",
        "comment": "Submitting for approval.",
        "is_draft": False,
        "recipient_user_id": 202,
        "recipient_username": "staff_202",
        "recipient_role": "Junior Superintendent",
    }
    res = c1.post("/api/v1/fts/files/", data=payload, format="json")
    assert res.status_code == status.HTTP_201_CREATED
    file_id = res.json()["id"]

    # Receiver sees it in Inbox
    inbox_res = c2.get("/api/v1/fts/inbox/")
    assert inbox_res.status_code == status.HTTP_200_OK
    assert any(f["id"] == file_id for f in inbox_res.json())

    # Sender sees it in Outbox
    outbox_res = c1.get("/api/v1/fts/outbox/")
    assert outbox_res.status_code == status.HTTP_200_OK
    assert any(f["id"] == file_id for f in outbox_res.json())


def test_draft_workflow(fts_client):
    client = fts_client(user_id=101)

    payload = {
        "subject": "Draft Requisition",
        "comment": "Draft comment.",
        "is_draft": True,
    }
    res = client.post("/api/v1/fts/files/", data=payload, format="json")
    assert res.status_code == status.HTTP_201_CREATED
    file_id = res.json()["id"]

    drafts = client.get("/api/v1/fts/drafts/").json()
    assert any(d["id"] == file_id for d in drafts)

    # Edit draft
    update_res = client.put(
        f"/api/v1/fts/files/{file_id}/",
        data={"subject": "Updated Draft Requisition", "comment": "Updated comment."},
        format="json",
    )
    assert update_res.status_code == status.HTTP_200_OK
    assert update_res.json()["subject"] == "Updated Draft Requisition"

    # Discard draft
    discard_res = client.post(f"/api/v1/fts/files/{file_id}/discard/")
    assert discard_res.status_code == status.HTTP_200_OK
    assert discard_res.json()["status"] == "DISCARDED"

    # Discarded draft no longer appears in drafts
    drafts_after = client.get("/api/v1/fts/drafts/").json()
    assert not any(d["id"] == file_id for d in drafts_after)


def test_forward_and_return_endpoints(fts_client):
    fts_client(user_id=101)
    c2 = fts_client(user_id=202)

    file_obj = create_file(
        subject="Leave Application",
        comment_text="Applying for casual leave.",
        actor_user_id=101,
        actor_username="fac_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Junior Superintendent",
    )

    # Recipient forwards to Dean (303)
    fwd_res = c2.post(
        f"/api/v1/fts/files/{file_obj.id}/forward/",
        data={
            "to_user_id": 303,
            "to_username": "dean_303",
            "to_role": "Dean Academic",
            "comment": "Recommended.",
        },
        format="json",
    )
    assert fwd_res.status_code == status.HTTP_200_OK
    assert fwd_res.json()["sequence"] == 2

    # Dean (303) returns file back to staff_202
    c3 = fts_client(user_id=303)
    ret_res = c3.post(
        f"/api/v1/fts/files/{file_obj.id}/return/",
        data={"comment": "Please verify balance."},
        format="json",
    )
    assert ret_res.status_code == status.HTTP_200_OK
    assert ret_res.json()["sequence"] == 3
    assert ret_res.json()["to_user_id"] == 202


def test_archive_endpoint(fts_client):
    file_obj = create_file(
        subject="Completed Project",
        comment_text="Initiating project.",
        actor_user_id=101,
        actor_username="fac_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Junior Superintendent",
    )

    # Non-owner gets 403 Forbidden
    res_forbidden = fts_client(user_id=202).post(f"/api/v1/fts/files/{file_obj.id}/archive/")
    assert res_forbidden.status_code == status.HTTP_403_FORBIDDEN

    # Owner archives successfully
    res_archive = fts_client(user_id=101).post(f"/api/v1/fts/files/{file_obj.id}/archive/")
    assert res_archive.status_code == status.HTTP_200_OK
    assert res_archive.json()["status"] == "ARCHIVED"


def test_history_and_governance_endpoints(fts_client, admin_client):
    client = fts_client(user_id=101)
    file_obj = create_file(
        subject="Governance File",
        comment_text="Initial comment.",
        actor_user_id=101,
        actor_username="fac_101",
        actor_role="Assistant Professor",
        is_draft=True,
    )

    hist_res = client.get(f"/api/v1/fts/files/{file_obj.id}/history/")
    assert hist_res.status_code == status.HTTP_200_OK
    assert len(hist_res.json()) >= 1

    admin = admin_client()
    logs_res = admin.get("/api/v1/fts/governance/audit-logs/")
    assert logs_res.status_code == status.HTTP_200_OK
    assert len(logs_res.json()) >= 1

    usage_res = admin.get("/api/v1/fts/governance/usage/")
    assert usage_res.status_code == status.HTTP_200_OK
    assert usage_res.json()["total_files"] >= 1
