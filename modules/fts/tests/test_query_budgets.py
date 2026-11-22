"""Query budget tests for FTS list and history endpoints to prevent N+1 queries."""
import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from modules.fts.services.files import create_file
from modules.fts.services.movements import forward_file

pytestmark = pytest.mark.django_db


@pytest.fixture
def fts_files_fixture():
    for i in range(5):
        f = create_file(
            subject=f"Budget File {i}",
            comment_text=f"Initial comment {i}.",
            actor_user_id=101,
            actor_username="faculty_101",
            actor_role="Assistant Professor",
            is_draft=False,
            recipient_user_id=202,
            recipient_username="staff_202",
            recipient_role="Junior Superintendent",
        )
        forward_file(
            file_id=f.id,
            actor_user_id=202,
            actor_username="staff_202",
            actor_role="Junior Superintendent",
            to_user_id=303,
            to_username="dean_303",
            to_role="Dean Academic",
            comment_text=f"Forward comment {i}.",
        )


def test_inbox_query_count_does_not_grow_with_rows(fts_client, fts_files_fixture):
    client = fts_client(user_id=303)

    with CaptureQueriesContext(connection) as first:
        res1 = client.get("/api/v1/fts/inbox/")
        assert res1.status_code == 200

    # Add 5 more files
    for i in range(5, 10):
        create_file(
            subject=f"Budget File {i}",
            comment_text=f"Initial comment {i}.",
            actor_user_id=101,
            actor_username="faculty_101",
            actor_role="Assistant Professor",
            is_draft=False,
            recipient_user_id=303,
            recipient_username="dean_303",
            recipient_role="Dean Academic",
        )

    with CaptureQueriesContext(connection) as second:
        res2 = client.get("/api/v1/fts/inbox/")
        assert res2.status_code == 200

    assert len(second) == len(first), (
        f"{len(first)} queries initially, {len(second)} after adding rows — N+1 query detected"
    )


def test_history_query_budget(fts_client):
    client = fts_client(user_id=101)
    f = create_file(
        subject="History Budget File",
        comment_text="Initial comment.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Junior Superintendent",
    )
    for step in range(4):
        forward_file(
            file_id=f.id,
            actor_user_id=202,
            actor_username="staff_202",
            actor_role="Junior Superintendent",
            to_user_id=202,
            to_username="staff_202",
            to_role="Junior Superintendent",
            comment_text=f"Step {step} comment.",
        )

    with CaptureQueriesContext(connection) as ctx:
        res = client.get(f"/api/v1/fts/files/{f.id}/history/")
        assert res.status_code == 200
        assert len(res.json()) >= 5

    # Should fetch with small constant number of queries using prefetch_related
    assert len(ctx) <= 5
