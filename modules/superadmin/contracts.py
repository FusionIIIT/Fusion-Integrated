from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from modules.superadmin.models.archival import ArchivedUserRecord, HistoricalDataArchive
from modules.superadmin.selectors.config import get_active_policy_param


@dataclass(frozen=True)
class ArchivedUserDTO:
    user_id: int
    institute_id: str
    username: str
    status: str
    archived_at: datetime
    reversible_until: datetime
    is_restorable: bool


@dataclass(frozen=True)
class PolicyParameterDTO:
    key: str
    value: Any
    value_type: str
    version: int
    effective_from: datetime


def get_archived_user_statuses(user_ids: Sequence[int]) -> dict[int, ArchivedUserDTO | None]:
    # Plural batch lookup of user archival statuses
    ids = sorted({int(uid) for uid in user_ids if uid is not None})
    if not ids:
        return {}
    records = {r.user_id: r for r in ArchivedUserRecord.objects.filter(user_id__in=ids)}
    result: dict[int, ArchivedUserDTO | None] = {}
    for uid in ids:
        rec = records.get(uid)
        if rec is None:
            result[uid] = None
        else:
            result[uid] = ArchivedUserDTO(
                user_id=rec.user_id,
                institute_id=rec.institute_id,
                username=rec.username,
                status=rec.status,
                archived_at=rec.archived_at,
                reversible_until=rec.reversible_until,
                is_restorable=(rec.status == "reversible"),
            )
    return result


def get_active_system_policies(keys: Sequence[str]) -> dict[str, PolicyParameterDTO]:
    # Plural batch lookup of current effective-dated governance policies
    result: dict[str, PolicyParameterDTO] = {}
    for k in keys:
        param = get_active_policy_param(k)
        if param is not None:
            result[k] = PolicyParameterDTO(
                key=param.key,
                value=param.value,
                value_type=param.value_type,
                version=param.version,
                effective_from=param.effective_from,
            )
    return result


def get_purged_dataset_statuses(dataset_keys: Sequence[str]) -> dict[str, bool]:
    # Plural verification of whether datasets have been permanently purged
    if not dataset_keys:
        return {}
    categories = set(dataset_keys)
    archives = HistoricalDataArchive.objects.filter(dataset_category__in=categories)
    cat_to_purged: dict[str, bool] = {}
    for a in archives:
        cat_to_purged[a.dataset_category] = a.is_purged
    return {k: cat_to_purged.get(k, False) for k in dataset_keys}
