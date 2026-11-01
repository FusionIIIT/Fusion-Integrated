"""Audit Service for System Admin Control Plane.

Maintains immutable audit evidence, structured action logging, and reporting
capabilities according to BR-SA-025, BR-SA-033, and CFR-SA-017 / CFR-SA-018.
"""
from datetime import datetime
from typing import Any
from django.utils import timezone
from modules.systemadmin.models.audit import SystemAdminAuditLog


class AuditService:
    @staticmethod
    def log_action(
        actor_username: str,
        action: str,
        result: str = "SUCCESS",
        target_user: str = "",
        target_role: str = "",
        ip_address: str | None = None,
        reason_or_context: str = "",
        metadata: dict[str, Any] | None = None,
        actor_role: str = "Super Admin",
    ) -> SystemAdminAuditLog:
        """Create an immutable audit log entry."""
        log_entry = SystemAdminAuditLog.objects.create(
            actor_username=actor_username or "system",
            actor_role=actor_role,
            action=action,
            target_user=target_user or "",
            target_role=target_role or "",
            ip_address=ip_address,
            result=result,
            reason_or_context=reason_or_context or "",
            metadata=metadata or {},
        )
        return log_entry

    @staticmethod
    def get_audit_logs(
        actor_username: str | None = None,
        action: str | None = None,
        result: str | None = None,
        target_user: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        search_query: str | None = None,
    ):
        """Query immutable audit logs with flexible filtering."""
        qs = SystemAdminAuditLog.objects.all().order_by("-timestamp")
        if actor_username:
            qs = qs.filter(actor_username__icontains=actor_username)
        if action:
            qs = qs.filter(action=action)
        if result:
            qs = qs.filter(result=result)
        if target_user:
            qs = qs.filter(target_user__icontains=target_user)
        if date_from:
            qs = qs.filter(timestamp__gte=date_from)
        if date_to:
            qs = qs.filter(timestamp__lte=date_to)
        if search_query:
            qs = qs.filter(reason_or_context__icontains=search_query)
        return qs

    @staticmethod
    def aggregate_audit_summary(date_from=None, date_to=None) -> dict[str, Any]:
        """Aggregate summary metrics for reports and dashboards."""
        qs = SystemAdminAuditLog.objects.all()
        if date_from:
            qs = qs.filter(timestamp__gte=date_from)
        if date_to:
            qs = qs.filter(timestamp__lte=date_to)

        total_actions = qs.count()
        success_count = qs.filter(result="SUCCESS").count()
        failure_count = qs.filter(result="FAILURE").count()
        rejected_count = qs.filter(result="REJECTED").count()

        actions_by_type = {}
        for row in qs.values("action"):
            act = row["action"]
            actions_by_type[act] = actions_by_type.get(act, 0) + 1

        top_actors = {}
        for row in qs.values("actor_username"):
            actor = row["actor_username"]
            top_actors[actor] = top_actors.get(actor, 0) + 1

        return {
            "total_actions": total_actions,
            "success_count": success_count,
            "failure_count": failure_count,
            "rejected_count": rejected_count,
            "actions_by_type": actions_by_type,
            "top_actors": top_actors,
        }


log_action = AuditService.log_action
get_audit_logs = AuditService.get_audit_logs
aggregate_audit_summary = AuditService.aggregate_audit_summary
