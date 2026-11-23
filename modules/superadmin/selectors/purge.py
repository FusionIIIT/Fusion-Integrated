from __future__ import annotations

from django.db.models import QuerySet

from fusion_auth.principal import Principal
from modules.superadmin.models.archival import PurgeRequest
from modules.superadmin.selectors.scoping import scope_purge_requests


def list_purge_requests(
    principal: Principal, *, status: str | None = None
) -> QuerySet[PurgeRequest]:
    qs = scope_purge_requests(principal)
    if status:
        qs = qs.filter(status=status)
    return qs


def get_purge_request(principal: Principal, request_id: int) -> PurgeRequest | None:
    return scope_purge_requests(principal).filter(id=request_id).first()
