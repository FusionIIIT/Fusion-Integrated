from __future__ import annotations

from django.db.models import QuerySet

from fusion_auth.principal import Principal
from modules.superadmin.models.archival import (
    ArchivedUserRecord,
    HistoricalDataArchive,
    PurgeRequest,
)
from modules.superadmin.models.audit import SuperAdminAuditLog


def scope_archived_users(principal: Principal) -> QuerySet[ArchivedUserRecord]:
    # Returns 404 rather than 403 on missing permission via empty queryset
    if not principal.has_permission("superadmin.archival.view"):
        return ArchivedUserRecord.objects.none()
    return ArchivedUserRecord.objects.all().order_by("-archived_at")


def scope_historical_archives(principal: Principal) -> QuerySet[HistoricalDataArchive]:
    # Historical datasets visible to users with archival view permission
    if not principal.has_permission("superadmin.archival.view"):
        return HistoricalDataArchive.objects.none()
    return HistoricalDataArchive.objects.all().order_by("-created_at")


def scope_purge_requests(principal: Principal) -> QuerySet[PurgeRequest]:
    # Dual-auth scoping: IT Head sees all for review; Super Admin sees their own
    if not principal.has_permission("superadmin.purge.view"):
        return PurgeRequest.objects.none()
    qs = PurgeRequest.objects.select_related("archive").all()
    if principal.has_permission("superadmin.purge.change"):
        return qs.order_by("-requested_at")
    return qs.filter(requested_by=principal.user_id).order_by("-requested_at")


def scope_audit_logs(principal: Principal) -> QuerySet[SuperAdminAuditLog]:
    # Compliance audit logs visible only to audit.view holders
    if not principal.has_permission("superadmin.audit.view"):
        return SuperAdminAuditLog.objects.none()
    return SuperAdminAuditLog.objects.all().order_by("-timestamp")
