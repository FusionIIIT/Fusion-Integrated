"""Dashboard metrics selector for System Admin module.

Computes PS-defined dashboard metrics (CFR-SA-018, AFR-SA-066, PS 3.4.3):
- User counts and status distribution
- Role counts, occupancy, upcoming expiry
- Recent administrative actions
- Archive volume and operations
- Security indicators (failed logins, active sessions, alerts)
"""
from datetime import date, timedelta
from typing import Any
from django.db.models import Count
from django.utils import timezone

from modules.system_admin.models import (
    ArchivedRecord,
    AuditLog,
    BasicUser,
    FailedLoginAttempt,
    PurgeRequest,
    RoleAssignment,
    RoleDefinition,
    SuperAdminSession,
)


def get_admin_dashboard_metrics() -> dict[str, Any]:
    now = timezone.now()
    today = date.today()
    last_24h = now - timedelta(hours=24)
    expiry_lead_date = today + timedelta(days=30)

    # 1. User metrics
    user_counts_by_status = dict(
        BasicUser.objects.values("status").annotate(count=Count("user_id")).values_list("status", "count")
    )
    user_counts_by_type = dict(
        BasicUser.objects.values("user_type").annotate(count=Count("user_id")).values_list("user_type", "count")
    )
    total_users = sum(user_counts_by_status.values())

    # 2. Role metrics
    total_roles = RoleDefinition.objects.count()
    singular_roles = RoleDefinition.objects.filter(is_singular=True).count()
    active_assignments = RoleAssignment.objects.filter(status="active").count()
    scheduled_assignments = RoleAssignment.objects.filter(status="scheduled").count()
    upcoming_expiries = RoleAssignment.objects.filter(
        status="active",
        end_date__isnull=False,
        end_date__gte=today,
        end_date__lte=expiry_lead_date,
    ).count()

    # 3. Archive metrics
    archived_users_count = BasicUser.objects.filter(status="archived").count()
    archived_records_count = ArchivedRecord.objects.filter(status="archived").count()
    pending_purges_count = PurgeRequest.objects.filter(status="pending_it_head").count()

    # 4. Security & monitoring metrics
    active_sessions_count = SuperAdminSession.objects.filter(is_active=True).count()
    failed_logins_24h = FailedLoginAttempt.objects.filter(attempted_at__gte=last_24h).count()

    # Consecutive failed logins check (alert threshold is 5 consecutive failures: BR-SA-024)
    recent_attempts = list(
        AuditLog.objects.filter(action="super_admin.login")
        .order_by("-timestamp")
        .values_list("result", flat=True)[:5]
    )
    security_alert_active = len(recent_attempts) == 5 and all(r == "failure" for r in recent_attempts)

    # 5. Recent audit actions
    recent_actions = list(
        AuditLog.objects.all()
        .order_by("-timestamp")
        .values("id", "timestamp", "actor_username", "action", "result", "target_type", "target_id")[:10]
    )

    return {
        "users": {
            "total": total_users,
            "active": user_counts_by_status.get("active", 0),
            "deactivated": user_counts_by_status.get("deactivated", 0),
            "archived": user_counts_by_status.get("archived", 0),
            "by_type": user_counts_by_type,
        },
        "roles": {
            "total_definitions": total_roles,
            "singular_definitions": singular_roles,
            "active_assignments": active_assignments,
            "scheduled_assignments": scheduled_assignments,
            "upcoming_expiries_30d": upcoming_expiries,
        },
        "archival": {
            "archived_users": archived_users_count,
            "archived_data_records": archived_records_count,
            "pending_purge_authorizations": pending_purges_count,
        },
        "security": {
            "active_sessions": active_sessions_count,
            "failed_logins_last_24h": failed_logins_24h,
            "consecutive_failed_login_alert": security_alert_active,
            "system_health": "nominal" if not security_alert_active else "warning",
        },
        "recent_activity": recent_actions,
    }
