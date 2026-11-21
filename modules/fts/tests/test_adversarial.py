"""Adversarial tests verifying refusal and boundary conditions in FTS."""
import pytest
from rest_framework import status

from modules.fts.services.archival import archive_file
from modules.fts.services.files import create_file

pytestmark = pytest.mark.django_db


def test_missing_mandatory_comment_rejected_at_api(fts_client):
    """BR-FTS-004, BR-FTS-006: Creation or movement without mandatory comment is rejected."""
    client = fts_client(user_id=101)
    res = client.post(
        "/api/v1/fts/files/",
        data={"subject": "No Comment File", "comment": "   ", "is_draft": True},
        format="json",
    )
    assert res.status_code == status.HTTP_400_BAD_REQUEST


def test_invalid_recipient_rejected_at_circulation(fts_client):
    """BR-FTS-007: Circulation without eligible recipient is rejected."""
    client = fts_client(user_id=101)
    res = client.post(
        "/api/v1/fts/files/",
        data={
            "subject": "Missing Recipient File",
            "comment": "Valid comment.",
            "is_draft": False,
            "recipient_user_id": None,
        },
        format="json",
    )
    assert res.status_code == status.HTTP_400_BAD_REQUEST


def test_hostile_query_parameter_returns_400_never_500(admin_client):
    """Hostile parameter formats return 400 Bad Request, never 500."""
    admin = admin_client()
    res = admin.get("/api/v1/fts/governance/audit-logs/?file_id=malicious_sql_injection")
    assert res.status_code == status.HTTP_400_BAD_REQUEST


def test_attempt_to_forward_archived_file_refused(fts_client):
    """BR-FTS-012: Archived file is immutable and cannot be forwarded."""
    file_obj = create_file(
        subject="Archived File",
        comment_text="Initial comment.",
        actor_user_id=101,
        actor_username="fac_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Junior Superintendent",
    )
    archive_file(
        file_id=file_obj.id,
        actor_user_id=101,
        actor_username="fac_101",
        actor_role="Assistant Professor",
    )

    client = fts_client(user_id=101)
    res = client.post(
        f"/api/v1/fts/files/{file_obj.id}/forward/",
        data={
            "to_user_id": 202,
            "to_username": "staff_202",
            "to_role": "Junior Superintendent",
            "comment": "Try forwarding archived file.",
        },
        format="json",
    )
    assert res.status_code == status.HTTP_409_CONFLICT
