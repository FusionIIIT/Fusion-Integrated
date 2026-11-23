from __future__ import annotations

from django.db.models import QuerySet

from fusion_auth.principal import Principal
from modules.superadmin.domain.constants import (
    ARCHIVAL_STATUS_REVERSIBLE,
    PURGE_STATUS_PENDING_IT_HEAD,
)
from modules.superadmin.models.archival import (
    ArchivedUserRecord,
    PurgeRequest,
)
from modules.superadmin.models.audit import SuperAdminAuditLog
from modules.superadmin.selectors.scoping import scope_audit_logs


def list_audit_logs(
    principal: Principal,
    *,
    actor_id: int | None = None,
    action: str | None = None,
) -> QuerySet[SuperAdminAuditLog]:
    qs = scope_audit_logs(principal)
    if actor_id is not None:
        qs = qs.filter(actor_id=actor_id)
    if action:
        qs = qs.filter(action=action)
    return qs


def get_dashboard_metrics(principal: Principal) -> dict[str, int]:
    # Aggregates metrics counts across governance models
    return {
        "archived_users_reversible": ArchivedUserRecord.objects.filter(
            status=ARCHIVAL_STATUS_REVERSIBLE
        ).count(),
        "archived_users_total": ArchivedUserRecord.objects.count(),
        "purge_requests_pending": PurgeRequest.objects.filter(
            status=PURGE_STATUS_PENDING_IT_HEAD
        ).count(),
        "audit_logs_total": SuperAdminAuditLog.objects.count(),
    }
