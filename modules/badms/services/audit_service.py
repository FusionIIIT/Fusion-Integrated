"""Audit logging service for BADMS (CFR-BA-018, BA-UC-023)."""

from __future__ import annotations

from typing import Any

from modules.badms.models import AuditLog


def record_audit_event(
    *,
    actor_id: int | None = None,
    actor_username: str = "",
    actor_role: str = "",
    event_source: str = "user",
    action: str,
    resource_type: str,
    resource_id: str = "",
    department_id: int | None = None,
    outcome: str = "success",
    details: dict[str, Any] | None = None,
    ip_address: str = "",
) -> AuditLog:
    """Creates an immutable audit log entry."""
    return AuditLog.objects.create(
        actor_id=actor_id,
        actor_username=actor_username,
        actor_role=actor_role,
        event_source=event_source,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        department_id=department_id,
        outcome=outcome,
        details=details or {},
        ip_address=ip_address,
    )
