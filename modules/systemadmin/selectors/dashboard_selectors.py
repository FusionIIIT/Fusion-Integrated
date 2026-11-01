"""Selectors for Aggregated Dashboard Metrics."""
from typing import Dict, Any
from django.utils import timezone
from django.db.models import Count, Q
from datetime import timedelta
from modules.systemadmin.models.user_mgmt import BasicUserProfile
from modules.systemadmin.models.role_mgmt import RoleDefinition, RoleAssignment
from modules.systemadmin.models.archival import ArchivedUser, ArchivedHistoricalData, PermanentPurgeRequest
from modules.systemadmin.models.audit import SystemAdminAuditLog, SessionLog, SecurityAlert


def get_dashboard_metrics() -> Dict[str, Any]:
    """Compile real-time overview metrics for System Admin Dashboard."""
    now = timezone.now()
    today = now.date()

    # User metrics
    total_users = BasicUserProfile.objects.count()
    active_users = BasicUserProfile.objects.filter(status="active").count()
    deactivated_users = BasicUserProfile.objects.filter(status="deactivated").count()
    archived_users = BasicUserProfile.objects.filter(status="archived").count()

    users_by_type = list(
        BasicUserProfile.objects.values("user_type")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    # Role metrics
    total_roles = RoleDefinition.objects.count()
    active_assignments = RoleAssignment.objects.filter(status__in=["active", "extended"]).count()

    # Find vacant singular roles
    singular_roles = RoleDefinition.objects.filter(is_singular=True, status="available")
    vacant_singular_roles = []
    for r in singular_roles:
        has_active = RoleAssignment.objects.filter(role=r, status__in=["active", "extended"]).exists()
        if not has_active:
            vacant_singular_roles.append({
                "id": r.id,
                "code": r.code,
                "name": r.name,
                "module_or_dept": r.module_or_dept,
            })

    # Upcoming expiries within 30 days
    thirty_days_later = today + timedelta(days=30)
    expiring_soon_count = RoleAssignment.objects.filter(
        status__in=["active", "extended"],
        end_date__isnull=False,
        end_date__gte=today,
        end_date__lte=thirty_days_later,
    ).count()

    # Archival & Purge metrics
    reversible_archived_count = ArchivedUser.objects.filter(status="reversible").count()
    permanent_archived_count = ArchivedUser.objects.filter(status="permanent_non_restorable").count()
    historical_batches_count = ArchivedHistoricalData.objects.filter(status="archived").count()
    pending_purge_requests = PermanentPurgeRequest.objects.filter(status="pending_it_head").count()

    # Security & Audit metrics
    active_sessions = SessionLog.objects.filter(is_active=True).count()
    unresolved_alerts = SecurityAlert.objects.filter(is_resolved=False).count()
    recent_failures_24h = SystemAdminAuditLog.objects.filter(
        result__in=["FAILURE", "REJECTED"],
        timestamp__gte=now - timedelta(hours=24),
    ).count()

    recent_actions = list(
        SystemAdminAuditLog.objects.all().order_by("-timestamp")[:8].values(
            "id", "timestamp", "actor_username", "action", "target_user", "target_role", "result"
        )
    )

    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "deactivated": deactivated_users,
            "archived": archived_users,
            "by_type": users_by_type,
        },
        "roles": {
            "total_defined": total_roles,
            "active_assignments": active_assignments,
            "vacant_singular_count": len(vacant_singular_roles),
            "vacant_singular_roles": vacant_singular_roles,
            "expiring_soon_count": expiring_soon_count,
        },
        "archival": {
            "reversible_users": reversible_archived_count,
            "permanent_users": permanent_archived_count,
            "historical_batches": historical_batches_count,
            "pending_purge_requests": pending_purge_requests,
        },
        "security": {
            "active_sessions": active_sessions,
            "unresolved_alerts": unresolved_alerts,
            "recent_failures_24h": recent_failures_24h,
            "recent_actions": recent_actions,
        },
    }
