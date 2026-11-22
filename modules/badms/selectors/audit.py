"""Read-only selectors for audit logs."""

from __future__ import annotations

from django.db.models import QuerySet

from modules.badms.models import AuditLog


def list_audit_logs(
    *,
    actor_id: int | None = None,
    event_source: str | None = None,
    department_id: int | None = None,
    action: str | None = None,
) -> QuerySet[AuditLog]:
    qs = AuditLog.objects.all().order_by("-created_at")
    if actor_id is not None:
        qs = qs.filter(actor_id=actor_id)
    if event_source:
        qs = qs.filter(event_source=event_source)
    if department_id is not None:
        qs = qs.filter(department_id=department_id)
    if action:
        qs = qs.filter(action=action)
    return qs
