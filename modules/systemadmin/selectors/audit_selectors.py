"""Selectors for Audit Logs, Sessions, Security Alerts, and Notifications."""

from typing import Any

from django.db.models import Count, Q, QuerySet

from modules.systemadmin.models.audit import (
    AdminNotification,
    SecurityAlert,
    SessionLog,
    SystemAdminAuditLog,
)


def list_audit_logs(
    actor_username: str | None = None,
    action: str | None = None,
    result: str | None = None,
    target_user: str | None = None,
    start_date: Any | None = None,
    end_date: Any | None = None,
    search: str | None = None,
) -> QuerySet[SystemAdminAuditLog]:
    """Retrieve immutable audit logs filtered by multiple criteria."""
    qs = SystemAdminAuditLog.objects.all()

    if actor_username:
        qs = qs.filter(actor_username__icontains=actor_username)
    if action:
        qs = qs.filter(action=action)
    if result:
        qs = qs.filter(result=result)
    if target_user:
        qs = qs.filter(target_user__icontains=target_user)
    if start_date:
        qs = qs.filter(timestamp__date__gte=start_date)
    if end_date:
        qs = qs.filter(timestamp__date__lte=end_date)
    if search:
        qs = qs.filter(
            Q(actor_username__icontains=search)
            | Q(action__icontains=search)
            | Q(target_user__icontains=search)
            | Q(reason_or_context__icontains=search)
        )

    return qs.order_by("-timestamp")


def get_audit_log_by_id(log_id: int) -> SystemAdminAuditLog | None:
    """Retrieve a single audit log entry by ID."""
    return SystemAdminAuditLog.objects.filter(id=log_id).first()


def list_session_logs(
    username: str | None = None,
    is_active: bool | None = None,
) -> QuerySet[SessionLog]:
    """Retrieve administrator session logs."""
    qs = SessionLog.objects.all()
    if username:
        qs = qs.filter(username__icontains=username)
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    return qs.order_by("-started_at")


def list_security_alerts(
    severity: str | None = None,
    is_resolved: bool | None = None,
) -> QuerySet[SecurityAlert]:
    """Retrieve security alerts."""
    qs = SecurityAlert.objects.all()
    if severity:
        qs = qs.filter(severity=severity)
    if is_resolved is not None:
        qs = qs.filter(is_resolved=is_resolved)
    return qs.order_by("-dispatched_at")


def list_notifications(
    recipient_username: str | None = None,
    is_read: bool | None = None,
    category: str | None = None,
) -> QuerySet[AdminNotification]:
    """Retrieve notifications."""
    qs = AdminNotification.objects.all()
    if recipient_username:
        qs = qs.filter(recipient_username=recipient_username)
    if is_read is not None:
        qs = qs.filter(is_read=is_read)
    if category:
        qs = qs.filter(category=category)
    return qs.order_by("-created_at")


def get_audit_metrics_summary(
    start_date: Any | None = None,
    end_date: Any | None = None,
) -> dict[str, Any]:
    """Aggregate audit activity metrics for reporting and dashboard."""
    qs = SystemAdminAuditLog.objects.all()
    if start_date:
        qs = qs.filter(timestamp__date__gte=start_date)
    if end_date:
        qs = qs.filter(timestamp__date__lte=end_date)

    total_logs = qs.count()
    success_count = qs.filter(result="SUCCESS").count()
    failure_count = qs.filter(result="FAILURE").count()
    rejected_count = qs.filter(result="REJECTED").count()

    actions_breakdown = list(
        qs.values("action").annotate(count=Count("id")).order_by("-count")[:10]
    )

    top_actors = list(
        qs.values("actor_username").annotate(count=Count("id")).order_by("-count")[:10]
    )

    return {
        "total_actions": total_logs,
        "success_count": success_count,
        "failure_count": failure_count,
        "rejected_count": rejected_count,
        "actions_breakdown": actions_breakdown,
        "top_actors": top_actors,
    }
