"""Audit selectors for System Admin module.

Enforces read-only inspection of immutable audit evidence (CFR-SA-018, AFR-SA-064, BR-SA-025).
"""
from datetime import datetime
from django.db.models import QuerySet

from modules.system_admin.models import AuditLog


def list_audit_logs(
    *,
    actor_username: str | None = None,
    action: str | None = None,
    result: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
) -> QuerySet[AuditLog]:
    """Provides read-only filtered access to audit logs."""
    qs = AuditLog.objects.all().order_by("-timestamp")

    if actor_username:
        qs = qs.filter(actor_username__icontains=actor_username.strip())
    if action:
        qs = qs.filter(action__iexact=action.strip())
    if result:
        qs = qs.filter(result=result)
    if start_time:
        qs = qs.filter(timestamp__gte=start_time)
    if end_time:
        qs = qs.filter(timestamp__lte=end_time)
    if target_type:
        qs = qs.filter(target_type=target_type)
    if target_id:
        qs = qs.filter(target_id=target_id)

    return qs


def get_audit_log_entry(log_id: int) -> AuditLog | None:
    return AuditLog.objects.filter(id=log_id).first()
