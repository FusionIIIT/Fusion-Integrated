from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class BackupStatusDTO:
    id: int
    backup_type: str
    dataset_name: str
    status: str
    checksum_sha256: str


@dataclass(frozen=True)
class ArchivalStatusDTO:
    id: int
    requester_user_id: int
    department: str
    status: str
    authoritative_classification: str
    is_encrypted: bool


@dataclass(frozen=True)
class UserStorageQuotaDTO:
    user_id: int
    allocated_quota_bytes: int
    used_storage_bytes: int
    is_full: bool


def get_backup_statuses(backup_ids: Sequence[int]) -> dict[int, BackupStatusDTO]:
    from modules.badms.models import BackupRecord

    ids = {int(i) for i in backup_ids if i is not None}
    if not ids:
        return {}
    records = BackupRecord.objects.filter(id__in=ids)
    return {
        r.id: BackupStatusDTO(
            id=r.id,
            backup_type=r.backup_type,
            dataset_name=r.dataset_name,
            status=r.status,
            checksum_sha256=r.checksum_sha256,
        )
        for r in records
    }


def get_archival_statuses(request_ids: Sequence[int]) -> dict[int, ArchivalStatusDTO]:
    from modules.badms.models import ArchivalRequest

    ids = {int(i) for i in request_ids if i is not None}
    if not ids:
        return {}
    records = ArchivalRequest.objects.filter(id__in=ids)
    return {
        r.id: ArchivalStatusDTO(
            id=r.id,
            requester_user_id=r.requester_user_id,
            department=r.department,
            status=r.status,
            authoritative_classification=r.authoritative_classification or "",
            is_encrypted=r.is_encrypted,
        )
        for r in records
    }


def get_user_storage_quotas(user_ids: Sequence[int]) -> dict[int, UserStorageQuotaDTO]:
    from modules.badms.models import UserStorageQuota

    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    existing = {q.user_id: q for q in UserStorageQuota.objects.filter(user_id__in=ids)}
    result: dict[int, UserStorageQuotaDTO] = {}
    for uid in ids:
        q = existing.get(uid)
        if q:
            result[uid] = UserStorageQuotaDTO(
                user_id=q.user_id,
                allocated_quota_bytes=q.allocated_quota_bytes,
                used_storage_bytes=q.used_storage_bytes,
                is_full=q.is_full,
            )
        else:
            created = UserStorageQuota.objects.create(
                user_id=uid,
                allocated_quota_bytes=10737418240,
                used_storage_bytes=0,
                is_full=False,
            )
            result[uid] = UserStorageQuotaDTO(
                user_id=created.user_id,
                allocated_quota_bytes=created.allocated_quota_bytes,
                used_storage_bytes=created.used_storage_bytes,
                is_full=created.is_full,
            )
    return result
