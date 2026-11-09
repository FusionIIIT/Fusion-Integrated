"""Administrative dashboard aggregations for system_admin (UC-SA-026)."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict

from django.utils import timezone

from modules.system_admin.constants import (
    PurgeRequestStatus,
    RoleAssignmentState,
    UserArchivalStatus,
    UserKind,
    UserLifecycleStatus,
)
from modules.system_admin.models import (
    ArchivedUserRecord,
    BasicUser,
    HistoricalDataArchive,
    PurgeRequest,
    RoleAssignment,
    SuperAdminSession,
)


def get_super_admin_dashboard_metrics() -> Dict[str, Any]:
    """Aggregate real-time metrics across all domain aggregates."""
    today = date.today()
    now = timezone.now()

    # User breakdown
    users_qs = BasicUser.objects.all()
    active_students = users_qs.filter(
        kind=UserKind.STUDENT, status=UserLifecycleStatus.ACTIVE
    ).count()
    active_faculty = users_qs.filter(
        kind=UserKind.FACULTY, status=UserLifecycleStatus.ACTIVE
    ).count()
    active_staff = users_qs.filter(
        kind=UserKind.STAFF, status=UserLifecycleStatus.ACTIVE
    ).count()
    deactivated_count = users_qs.filter(
        status=UserLifecycleStatus.DEACTIVATED
    ).count()

    # Archival breakdown
    archived_reversible = ArchivedUserRecord.objects.filter(
        status=UserArchivalStatus.REVERSIBLE, reversible_until__gte=now
    ).count()
    archived_permanent = ArchivedUserRecord.objects.filter(
        status=UserArchivalStatus.PERMANENT_NON_RESTORABLE
    ).count()

    # Role metrics
    active_roles_count = RoleAssignment.objects.filter(
        state__in=[RoleAssignmentState.ACTIVE, RoleAssignmentState.EXTENDED]
    ).count()
    roles_expiring_soon = RoleAssignment.objects.filter(
        state__in=[RoleAssignmentState.ACTIVE, RoleAssignmentState.EXTENDED],
        end_date__isnull=False,
        end_date__gte=today,
        end_date__lte=today + timedelta(days=7),
    ).count()

    # Purge metrics
    pending_purges = PurgeRequest.objects.filter(
        status=PurgeRequestStatus.PENDING_IT_HEAD
    ).count()
    historical_archives_count = HistoricalDataArchive.objects.filter(
        is_purged=False
    ).count()

    # Security sessions
    active_sessions = SuperAdminSession.objects.filter(
        is_active=True, expires_at__gt=now
    ).count()

    return {
        "users": {
            "active_students": active_students,
            "active_faculty": active_faculty,
            "active_staff": active_staff,
            "deactivated": deactivated_count,
            "total_active": active_students + active_faculty + active_staff,
        },
        "roles": {
            "active_assignments": active_roles_count,
            "expiring_within_7_days": roles_expiring_soon,
        },
        "archival": {
            "reversible_users": archived_reversible,
            "permanent_archived_users": archived_permanent,
            "retained_historical_archives": historical_archives_count,
            "pending_purge_requests": pending_purges,
        },
        "security": {
            "active_super_admin_sessions": active_sessions,
        },
    }
