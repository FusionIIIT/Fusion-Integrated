"""End-to-end journey tests for FTS collaborative workflows."""
import pytest
from rest_framework import status

pytestmark = pytest.mark.django_db


def test_complete_file_lifecycle_journey(fts_client):
    # Step 1: Creator creates draft (BW-FTS-05 / CW-FTS-02)
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

    # Step 2: Creator edits draft (BW-FTS-06)
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

    # Step 3: Creator submits and forwards to Staff (initial circulation)
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

    # Step 4: Staff sees in Inbox and forwards to Dean Academic (BW-FTS-01, BW-FTS-02)
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

    # Step 5: Dean Academic returns to Staff for clarification (BW-FTS-03)
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

    # Step 7: File Owner archives completed file (BW-FTS-04, CW-FTS-01)
    res_archive = fts_client(user_id=101).post(f"/api/v1/fts/files/{file_id}/archive/")
    assert res_archive.status_code == status.HTTP_200_OK
    assert res_archive.json()["status"] == "ARCHIVED"

    # Step 8: Full history is chronological and accessible to all participants
    history = fts_client(user_id=303).get(f"/api/v1/fts/files/{file_id}/history/").json()
    assert len(history) >= 4
    sequences = [m["sequence"] for m in history]
    assert sequences == sorted(sequences)
