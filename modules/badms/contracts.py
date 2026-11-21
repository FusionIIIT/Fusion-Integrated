"""Public contract for BADMS module. Plural signatures only."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from modules.badms.models import SecureArchivalRequest, StorageQuota


@dataclass(frozen=True)
class UserStorageDTO:
    user_id: int
    allocated_mb: int
    used_mb: int
    is_quota_full: bool


def get_user_storage_quotas(user_ids: Sequence[int]) -> dict[int, UserStorageDTO]:
    """Returns storage quota status for multiple users."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    quotas = StorageQuota.objects.filter(user_id__in=ids)
    res = {}
    for q in quotas:
        res[q.user_id] = UserStorageDTO(
            user_id=q.user_id,
            allocated_mb=q.allocated_mb,
            used_mb=q.used_mb,
            is_quota_full=(q.used_mb >= q.allocated_mb),
        )
    for uid in ids:
        if uid not in res:
            res[uid] = UserStorageDTO(user_id=uid, allocated_mb=5120, used_mb=0, is_quota_full=False)
    return res


@dataclass(frozen=True)
class ArchivalStatusDTO:
    user_id: int
    archival_count: int
    pending_count: int


def get_archival_statuses(user_ids: Sequence[int]) -> dict[int, ArchivalStatusDTO]:
    """Returns summary counts of archival requests for multiple users."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    res = {}
    for uid in ids:
        reqs = SecureArchivalRequest.objects.filter(user_id=uid)
        total = reqs.count()
        pending = reqs.exclude(status__in=["completed", "hod_rejected"]).count()
        res[uid] = ArchivalStatusDTO(user_id=uid, archival_count=total, pending_count=pending)
    return res
