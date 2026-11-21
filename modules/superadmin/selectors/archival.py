from __future__ import annotations

from django.db.models import Q, QuerySet

from fusion_auth.principal import Principal
from modules.superadmin.models.archival import (
    ArchivedUserRecord,
    HistoricalDataArchive,
)
from modules.superadmin.selectors.scoping import (
    scope_archived_users,
    scope_historical_archives,
)


def list_archived_users(
    principal: Principal,
    *,
    status: str | None = None,
    search: str | None = None,
) -> QuerySet[ArchivedUserRecord]:
    qs = scope_archived_users(principal)
    if status:
        qs = qs.filter(status=status)
    if search:
        s = search.strip()
        qs = qs.filter(
            Q(username__icontains=s) | Q(institute_id__icontains=s) | Q(email__icontains=s)
        )
    return qs


def get_archived_user(principal: Principal, user_id: int) -> ArchivedUserRecord | None:
    return scope_archived_users(principal).filter(user_id=user_id).first()


def list_historical_archives(
    principal: Principal,
    *,
    category: str | None = None,
) -> QuerySet[HistoricalDataArchive]:
    qs = scope_historical_archives(principal)
    if category:
        qs = qs.filter(dataset_category=category)
    return qs


def get_historical_archive(principal: Principal, archive_id: int) -> HistoricalDataArchive | None:
    return scope_historical_archives(principal).filter(id=archive_id).first()
