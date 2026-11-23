"""Query count tests for BADMS list endpoints to prevent N+1 queries.
"""
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.badms.models import ArchivalRequest, BackupRecord, StorageExtensionRequest

pytestmark = pytest.mark.django_db


def _client(stub_iam, **kw):
    stub_iam(make_session(**kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def test_backup_list_query_budget(stub_iam, django_assert_num_queries):
    c = _client(
        stub_iam,
        user_id=1,
        roles=("SysAdmin",),
        active_role="SysAdmin",
        modules=("badms",),
        permissions=("badms.backup.view",),
    )

    BackupRecord.objects.create(
        backup_type="scheduled",
        dataset_name="db_1",
        status="success",
        file_path="/tmp/1.dump",
        file_size_bytes=100,
        checksum_sha256="abc",
    )

    with django_assert_num_queries(1):
        res1 = c.get("/api/v1/badms/backups/")
        assert res1.status_code == 200

    for i in range(2, 6):
        BackupRecord.objects.create(
            backup_type="scheduled",
            dataset_name=f"db_{i}",
            status="success",
            file_path=f"/tmp/{i}.dump",
            file_size_bytes=100,
            checksum_sha256="abc",
        )

    with django_assert_num_queries(1):
        res2 = c.get("/api/v1/badms/backups/")
        assert res2.status_code == 200
        assert len(res2.json()["results"]) == 5


def test_archival_request_list_query_budget(stub_iam, django_assert_num_queries):
    c = _client(
        stub_iam,
        user_id=1,
        roles=("SysAdmin",),
        active_role="SysAdmin",
        modules=("badms",),
        permissions=("badms.archival.view",),
    )

    ArchivalRequest.objects.create(
        requester_user_id=101,
        department="CSE",
        file_name="data_1.tar",
        file_type="tar",
        file_size_bytes=100,
        reason="test",
        file_storage_path="/tmp/1",
        initial_classification="Routine",
        status="submitted",
    )

    with django_assert_num_queries(1):
        res1 = c.get("/api/v1/badms/archival-requests/")
        assert res1.status_code == 200

    for i in range(2, 6):
        ArchivalRequest.objects.create(
            requester_user_id=100 + i,
            department="CSE",
            file_name=f"data_{i}.tar",
            file_type="tar",
            file_size_bytes=100,
            reason="test",
            file_storage_path=f"/tmp/{i}",
            initial_classification="Routine",
            status="submitted",
        )

    with django_assert_num_queries(1):
        res2 = c.get("/api/v1/badms/archival-requests/")
        assert res2.status_code == 200
        assert len(res2.json()["results"]) == 5


def test_storage_extension_list_query_budget(stub_iam, django_assert_num_queries):
    c = _client(
        stub_iam,
        user_id=901,
        roles=("HOD (CSE)",),
        active_role="HOD (CSE)",
        modules=("badms",),
        permissions=("badms.storage.view",),
    )

    StorageExtensionRequest.objects.create(
        requester_user_id=101,
        department="CSE",
        current_usage_bytes=500,
        current_quota_bytes=1000,
        requested_extension_bytes=1000,
        justification="Research dataset",
        status="submitted",
    )

    with django_assert_num_queries(1):
        res1 = c.get("/api/v1/badms/storage-extensions/")
        assert res1.status_code == 200

    for i in range(2, 6):
        StorageExtensionRequest.objects.create(
            requester_user_id=100 + i,
            department="CSE",
            current_usage_bytes=500,
            current_quota_bytes=1000,
            requested_extension_bytes=1000,
            justification=f"Research {i}",
            status="submitted",
        )

    with django_assert_num_queries(1):
        res2 = c.get("/api/v1/badms/storage-extensions/")
        assert res2.status_code == 200
        assert len(res2.json()["results"]) == 5
