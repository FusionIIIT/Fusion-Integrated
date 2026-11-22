"""BADMS public contract surface. Strictly plural by signature."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from modules.badms.models import ArchivalRequest, UserStorageQuota


@dataclass(frozen=True)
class UserStorageQuotaDTO:
    user_id: int
    used_bytes: int
    quota_bytes: int
    is_full: bool


@dataclass(frozen=True)
class UserArchivalSummaryDTO:
    user_id: int
    total_archived_files: int
    total_archived_bytes: int
    has_sensitive_data: bool


def get_user_storage_quotas(user_ids: Sequence[int]) -> dict[int, UserStorageQuotaDTO]:
    """Exposes current storage usage and quota states to external modules."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    quotas = UserStorageQuota.objects.filter(user_id__in=ids)
    result: dict[int, UserStorageQuotaDTO] = {}
    for q in quotas:
        result[q.user_id] = UserStorageQuotaDTO(
            user_id=q.user_id,
            used_bytes=q.used_bytes,
            quota_bytes=q.quota_bytes,
            is_full=q.is_full,
        )
    return result


def get_user_archival_summaries(user_ids: Sequence[int]) -> dict[int, UserArchivalSummaryDTO]:
    """Exposes archival statistics for users (e.g. for student clearance or directory profile)."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    requests = ArchivalRequest.objects.filter(user_id__in=ids)
    summaries: dict[int, dict] = {uid: {"count": 0, "bytes": 0, "sensitive": False} for uid in ids}

    for req in requests:
        summaries[req.user_id]["count"] += 1
        summaries[req.user_id]["bytes"] += req.file_size_bytes
        if (
            req.authoritative_classification == "sensitive"
            or req.initial_classification == "sensitive"
        ):
            summaries[req.user_id]["sensitive"] = True

    return {
        uid: UserArchivalSummaryDTO(
            user_id=uid,
            total_archived_files=data["count"],
            total_archived_bytes=data["bytes"],
            has_sensitive_data=data["sensitive"],
        )
        for uid, data in summaries.items()
    }
