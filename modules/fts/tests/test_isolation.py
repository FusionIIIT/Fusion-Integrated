"""Scoping isolation tests ensuring non-associated employees cannot access files."""
import pytest
from rest_framework import status

from modules.fts.services.files import create_file

pytestmark = pytest.mark.django_db


def test_unassociated_employee_cannot_view_file_or_history(fts_client):
    """BR-FTS-009, FTS-UC-007, BW-FTS-05: Non-associated employee cannot view file or tracking history."""
    c_unrelated = fts_client(user_id=999, kind="faculty", active_role="Associate Professor")

    file_obj = create_file(
        subject="Confidential Evaluation",
        comment_text="Private departmental note.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="faculty_202",
        recipient_role="HOD (ECE)",
    )

    # Unassociated user cannot view file details - answers 404 to avoid leaking existence
    detail_res = c_unrelated.get(f"/api/v1/fts/files/{file_obj.id}/")
    assert detail_res.status_code == status.HTTP_404_NOT_FOUND

    # Unassociated user cannot view tracking history - answers 404
    history_res = c_unrelated.get(f"/api/v1/fts/files/{file_obj.id}/history/")
    assert history_res.status_code == status.HTTP_404_NOT_FOUND

    # File does not leak into unassociated user's inbox or outbox
    inbox = c_unrelated.get("/api/v1/fts/inbox/").json()
    assert not any(f["id"] == file_obj.id for f in inbox)

    outbox = c_unrelated.get("/api/v1/fts/outbox/").json()
    assert not any(f["id"] == file_obj.id for f in outbox)
