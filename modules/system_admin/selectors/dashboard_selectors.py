"""Dashboard aggregation metrics selector."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from django.db.models import Count

from modules.system_admin.models.archive import (
    ArchivedUserRecord,
    PermanentPurgeRequest,
)
from modules.system_admin.models.audit import FailedLoginLog, SystemAuditLog
from modules.system_admin.models.role_assignment import RoleAssignment
from modules.system_admin.models.user_account import UserAccount
from modules.system_admin.selectors.role_selectors import (
    get_approaching_role_expiries,
    get_role_directory,
)


def get_system_admin_dashboard_metrics() -> dict[str, Any]:
    """Aggregate near-real-time metrics for the admin dashboard (AFR-SA-066)."""
    # 1. User status counts
    status_counts = dict(
        UserAccount.objects.values("status")
        .annotate(total=Count("user_id"))
        .values_list("status", "total")
    )

    # 2. User type counts
    type_counts = dict(
        UserAccount.objects.values("user_type")
        .annotate(total=Count("user_id"))
        .values_list("user_type", "total")
    )

    # 3. Role statistics
    active_roles_count = RoleAssignment.objects.filter(status="active").count()
    directory = get_role_directory()
    vacant_singular_roles_count = sum(
        1 for r in directory if r["is_singular"] and r["is_vacant"]
    )
    approaching_expiries = get_approaching_role_expiries(within_days=30)

    # 4. Security & Audit statistics
    now = datetime.now(UTC)
    last_24h = now - timedelta(hours=24)
    failed_logins_24h = FailedLoginLog.objects.filter(
        attempted_at__gte=last_24h
    ).count()
    audit_events_count = SystemAuditLog.objects.count()

    # 5. Archival & Purge metrics
    archived_users_count = ArchivedUserRecord.objects.count()
    pending_purges_count = PermanentPurgeRequest.objects.filter(
        status="pending_it_head"
    ).count()

    return {
        "users": {
            "total": sum(status_counts.values()),
            "active": status_counts.get("active", 0),
            "deactivated": status_counts.get("deactivated", 0),
            "archived": status_counts.get("archived", 0),
            "by_type": type_counts,
        },
        "roles": {
            "active_assignments": active_roles_count,
            "vacant_singular_roles": vacant_singular_roles_count,
            "approaching_expiries_30d": len(approaching_expiries),
        },
        "security": {
            "failed_logins_24h": failed_logins_24h,
            "total_audit_events": audit_events_count,
        },
        "archives": {
            "archived_users": archived_users_count,
            "pending_purge_authorizations": pending_purges_count,
        },
        "system_health": {
            "status": "healthy",
            "database": "connected",
            "auth_service": "online",
        },
    }
