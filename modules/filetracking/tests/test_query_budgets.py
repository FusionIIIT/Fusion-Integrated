"""Query budget tests ensuring list endpoints don't suffer from N+1 query leaks (Step 5.8)."""

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.filetracking.models import (
    FileMovement,
    FileStatus,
    TrackedFile,
)

pytestmark = pytest.mark.django_db


def _client(stub_iam, uid=10):
    stub_iam(
        make_session(
            user_id=uid,
            permissions=("filetracking.file.view", "filetracking.file.create"),
            modules=("filetracking",),
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token budget-token")
    return c


def _create_files(user_id: int, start_idx: int, count: int):
    for i in range(start_idx, start_idx + count):
        file = TrackedFile.objects.create(
            file_number=f"FTS-BUDGET-{user_id}-{i}",
            subject=f"Budget Test File {i}",
            status=FileStatus.CIRCULATING,
            created_by_user_id=user_id,
            current_holder_user_id=user_id,
        )
        FileMovement.objects.create(
            file=file,
            sequence_number=1,
            action="created",
            sender_user_id=user_id,
            sender_designation="faculty",
            receiver_user_id=user_id,
            receiver_designation="faculty",
            comment="Initial circulation note",
        )


def test_inbox_query_budget(stub_iam, django_assert_num_queries):
    client = _client(stub_iam, uid=10)
    _create_files(user_id=10, start_idx=0, count=2)

    with django_assert_num_queries(2):
        res2 = client.get("/api/v1/filetracking/files/inbox/")
        assert res2.status_code == 200
        assert len(res2.json()) == 2

    # Scale to 20 files
    _create_files(user_id=10, start_idx=2, count=18)
    with django_assert_num_queries(2):
        res20 = client.get("/api/v1/filetracking/files/inbox/")
        assert res20.status_code == 200
        assert len(res20.json()) == 20
