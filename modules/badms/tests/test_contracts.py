"""Tests for cross-module plural read-only contracts.
"""
import pytest

from modules.badms import contracts
from modules.badms.models import ArchivalRequest, BackupRecord, UserStorageQuota

pytestmark = pytest.mark.django_db


def test_contracts_empty_inputs():
    assert contracts.get_backup_statuses([]) == {}
    assert contracts.get_archival_statuses([]) == {}
    assert contracts.get_user_storage_quotas([]) == {}


def test_get_backup_statuses():
    b1 = BackupRecord.objects.create(
        backup_type="manual",
        dataset_name="db1",
        status="success",
        checksum_sha256="sha-1234",
    )
    b2 = BackupRecord.objects.create(
        backup_type="scheduled",
        dataset_name="db2",
        status="failure",
        checksum_sha256="",
    )

    res = contracts.get_backup_statuses([b1.id, b2.id, 9999])
    assert len(res) == 2
    assert res[b1.id].dataset_name == "db1"
    assert res[b1.id].status == "success"
    assert res[b1.id].checksum_sha256 == "sha-1234"
    assert res[b2.id].status == "failure"


def test_get_archival_statuses():
    a1 = ArchivalRequest.objects.create(
        requester_user_id=1001,
        department="CSE",
        file_name="file1.tar",
        file_type="archive",
        file_size_bytes=1000,
        file_storage_path="/p1",
        status="classified_sensitive",
        authoritative_classification="Sensitive",
        is_encrypted=False,
    )
    res = contracts.get_archival_statuses([a1.id])
    assert len(res) == 1
    assert res[a1.id].requester_user_id == 1001
    assert res[a1.id].department == "CSE"
    assert res[a1.id].authoritative_classification == "Sensitive"
    assert res[a1.id].is_encrypted is False


def test_get_user_storage_quotas_existing_and_new():
    UserStorageQuota.objects.create(
        user_id=1001,
        allocated_quota_bytes=2000,
        used_storage_bytes=1500,
        is_full=False,
    )
    # 2002 does not exist initially
    res = contracts.get_user_storage_quotas([1001, 2002])
    assert len(res) == 2
    assert res[1001].allocated_quota_bytes == 2000
    assert res[1001].used_storage_bytes == 1500

    # 2002 was provisioned with default 10GB baseline
    assert res[2002].user_id == 2002
    assert res[2002].allocated_quota_bytes == 10737418240
    assert res[2002].used_storage_bytes == 0
    assert res[2002].is_full is False
