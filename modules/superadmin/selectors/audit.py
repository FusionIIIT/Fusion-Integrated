"""Audit selectors for Super Admin."""

from __future__ import annotations

from django.db.models import QuerySet

from modules.superadmin.models import AuditLogRecord
from modules.superadmin.selectors.scoping import visible_audit_logs


def list_audit_logs(
    principal,
    *,
    actor_user_id: int | None = None,
    event_type: str = "",
    target_entity: str = "",
) -> QuerySet[AuditLogRecord]:
    qs = visible_audit_logs(principal)
    if actor_user_id is not None:
        qs = qs.filter(actor_user_id=actor_user_id)
    if event_type:
        qs = qs.filter(event_type__icontains=event_type)
    if target_entity:
        qs = qs.filter(target_entity=target_entity)
    return qs.order_by("-created_at")
