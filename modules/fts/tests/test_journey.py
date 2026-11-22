"""End-to-end journey tests for FTS collaborative workflows and alternate paths.

Validates BW-FTS-01 through BW-FTS-08, CW-FTS-01, CW-FTS-02, and Use Cases FTS-UC-001 through FTS-UC-010.
"""
from __future__ import annotations

import pytest
from rest_framework import status

pytestmark = pytest.mark.django_db


def test_complete_file_lifecycle_journey(fts_client):
    """BW-FTS-01, BW-FTS-02, BW-FTS-03, BW-FTS-04: Main circulation, forward, return, and archive journey."""
    # Step 1: Creator creates draft (BW-FTS-05 / FTS-UC-001 / FTS-UC-002)
    res_draft = fts_client(user_id=101, kind="faculty", active_role="Assistant Professor").post(
        "/api/v1/fts/files/",
        data={
            "subject": "Research Lab Infrastructure Proposal",
            "description": "Proposal for GPU workstations.",
            "comment": "Initial proposal draft.",
            "is_draft": True,
        },
        format="json",
    )
    assert res_draft.status_code == status.HTTP_201_CREATED
    file_id = res_draft.json()["id"]

    # Step 2: Creator edits draft (BW-FTS-06 / FTS-UC-003)
    res_edit = fts_client(user_id=101).put(
        f"/api/v1/fts/files/{file_id}/",
        data={
            "subject": "Research Lab High-Performance Computing Proposal",
            "description": "Revised proposal for NVIDIA GPU cluster.",
            "comment": "Added server specifications.",
        },
        format="json",
    )
    assert res_edit.status_code == status.HTTP_200_OK
    assert res_edit.json()["subject"] == "Research Lab High-Performance Computing Proposal"

    # Step 3: Creator submits and forwards to Staff (initial circulation: BW-FTS-01)
    res_circ = fts_client(user_id=101).post(
        f"/api/v1/fts/files/{file_id}/forward/",
        data={
            "to_user_id": 202,
            "to_username": "staff_202",
            "to_role": "Junior Superintendent",
            "comment": "Submitting proposal for budget scrutiny.",
        },
        format="json",
    )
    assert res_circ.status_code == status.HTTP_200_OK

    # Step 4: Staff sees in Inbox and forwards to Dean Academic (BW-FTS-02 / FTS-UC-005)
    inbox_staff = fts_client(user_id=202, kind="staff", active_role="Junior Superintendent").get(
        "/api/v1/fts/inbox/"
    ).json()
    assert any(f["id"] == file_id for f in inbox_staff)

    res_fwd = fts_client(user_id=202).post(
        f"/api/v1/fts/files/{file_id}/forward/",
        data={
            "to_user_id": 303,
            "to_username": "dean_303",
            "to_role": "Dean Academic",
            "comment": "Budget audited. Recommended for administrative approval.",
        },
        format="json",
    )
    assert res_fwd.status_code == status.HTTP_200_OK

    # Step 5: Dean Academic returns to Staff for clarification (BW-FTS-03 / FTS-UC-006)
    inbox_dean = fts_client(user_id=303, kind="faculty", active_role="Dean Academic").get(
        "/api/v1/fts/inbox/"
    ).json()
    assert any(f["id"] == file_id for f in inbox_dean)

    res_ret = fts_client(user_id=303).post(
        f"/api/v1/fts/files/{file_id}/return/",
        data={"comment": "Please verify vendor quotes and AMC costs."},
        format="json",
    )
    assert res_ret.status_code == status.HTTP_200_OK

    # Step 6: Staff answers clarification and forwards back to Dean Academic
    res_fwd2 = fts_client(user_id=202).post(
        f"/api/v1/fts/files/{file_id}/forward/",
        data={
            "to_user_id": 303,
            "to_username": "dean_303",
            "to_role": "Dean Academic",
            "comment": "Three quotes verified under GeM portal guidelines.",
        },
        format="json",
    )
    assert res_fwd2.status_code == status.HTTP_200_OK

    # Step 7: File Owner archives completed file (BW-FTS-04 / CW-FTS-01 / FTS-UC-007)
    res_archive = fts_client(user_id=101).post(f"/api/v1/fts/files/{file_id}/archive/")
    assert res_archive.status_code == status.HTTP_200_OK
    assert res_archive.json()["status"] == "ARCHIVED"

    # Step 8: Full history is chronological and accessible to all participants (BW-FTS-06)
    history = fts_client(user_id=303).get(f"/api/v1/fts/files/{file_id}/history/").json()
    assert len(history) >= 4
    sequences = [m["sequence"] for m in history]
    assert sequences == sorted(sequences)


def test_draft_lifecycle_and_discard_alternate_journey(fts_client):
    """BW-FTS-05, BW-FTS-07, FTS-UC-004: Alternate draft creation, editing, and discard journey."""
    client = fts_client(user_id=401, kind="faculty", active_role="Associate Professor")

    # Step 1: Create draft with attachment
    res_create = client.post(
        "/api/v1/fts/files/",
        data={
            "subject": "Preliminary Workshop Budget",
            "description": "Budget estimation for AI workshop.",
            "comment": "Initial draft preparation.",
            "is_draft": True,
            "attachments": [
                {
                    "file_name": "draft_schedule.pdf",
                    "file_url": "https://storage.fusion.ac.in/fts/sched.pdf",
                    "file_size": 102400,
                    "mime_type": "application/pdf",
                }
            ],
        },
        format="json",
    )
    assert res_create.status_code == status.HTTP_201_CREATED
    file_id = res_create.json()["id"]

    # Step 2: Verify file appears in user's drafts list
    drafts = client.get("/api/v1/fts/drafts/").json()
    assert any(d["id"] == file_id for d in drafts)

    # Step 3: Edit draft with updated description
    res_edit = client.put(
        f"/api/v1/fts/files/{file_id}/",
        data={
            "description": "Budget estimation for Winter AI workshop (revised).",
            "comment": "Updated target dates.",
        },
        format="json",
    )
    assert res_edit.status_code == status.HTTP_200_OK
    assert res_edit.json()["description"] == "Budget estimation for Winter AI workshop (revised)."

    # Step 4: Discard draft (BW-FTS-07 soft-delete terminal state)
    res_discard = client.post(f"/api/v1/fts/files/{file_id}/discard/")
    assert res_discard.status_code == status.HTTP_200_OK
    assert res_discard.json()["status"] == "DISCARDED"

    # Step 5: Verify draft is no longer in active drafts list
    drafts_after = client.get("/api/v1/fts/drafts/").json()
    assert not any(d["id"] == file_id for d in drafts_after)

    # Step 6: Verify file does not appear in inbox or outbox
    inbox = client.get("/api/v1/fts/inbox/").json()
    assert not any(f["id"] == file_id for f in inbox)

    outbox = client.get("/api/v1/fts/outbox/").json()
    assert not any(f["id"] == file_id for f in outbox)


def test_outbox_tracking_and_governance_inspection_journey(fts_client, admin_client):
    """BW-FTS-06, BW-FTS-08, FTS-UC-008, FTS-UC-009, FTS-UC-010: Outbox tracking and governance audit inspection."""
    c_author = fts_client(user_id=501, kind="faculty", active_role="Professor")

    # Step 1: Author immediately circulates a file to colleague
    res_circ = c_author.post(
        "/api/v1/fts/files/",
        data={
            "subject": "Departmental Equipment Procurement",
            "description": "Procurement of 5 oscilloscopes for electronics laboratory.",
            "comment": "Submitted for catalog verification.",
            "is_draft": False,
            "recipient_user_id": 602,
            "recipient_username": "staff_602",
            "recipient_role": "Junior Assistant",
            "attachments": [
                {
                    "file_name": "specs.pdf",
                    "file_url": "https://storage.fusion.ac.in/fts/specs.pdf",
                    "file_size": 204800,
                    "mime_type": "application/pdf",
                }
            ],
        },
        format="json",
    )
    assert res_circ.status_code == status.HTTP_201_CREATED
    file_id = res_circ.json()["id"]

    # Step 2: Author sees file in Outbox with colleague as current holder (FTS-UC-009)
    outbox = c_author.get("/api/v1/fts/outbox/").json()
    outbox_file = next((f for f in outbox if f["id"] == file_id), None)
    assert outbox_file is not None
    assert outbox_file["current_holder_user_id"] == 602
    assert outbox_file["status"] == "CIRCULATED"

    # Step 3: Colleague sees file in Inbox (FTS-UC-008)
    c_colleague = fts_client(user_id=602, kind="staff", active_role="Junior Assistant")
    inbox = c_colleague.get("/api/v1/fts/inbox/").json()
    assert any(f["id"] == file_id for f in inbox)

    # Step 4: Administrator views Governance metrics and audit logs (FTS-UC-010 / CFR-FTS-05)
    c_admin = admin_client(user_id=999)
    metrics = c_admin.get("/api/v1/fts/governance/usage/").json()
    assert metrics["total_files"] >= 1
    assert metrics["circulated_files"] >= 1

    audit_logs = c_admin.get(f"/api/v1/fts/governance/audit-logs/?file_id={file_id}").json()
    assert len(audit_logs) >= 1
    actions = [log["action"] for log in audit_logs]
    assert "FILE_CREATED" in actions
