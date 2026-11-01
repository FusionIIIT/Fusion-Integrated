"""Immutable audit service for PMS (BR-PMS-121, 122)."""

from __future__ import annotations

from typing import Any

from modules.pms.models import PatentApplication, PatentAuditLog


def record_audit_event(
    application: PatentApplication | None,
    user_id: int,
    actor_role: str,
    action_type: str,
    previous_state: str = "",
    new_state: str = "",
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> PatentAuditLog:
    """Record an immutable audit log entry for a critical action or transition."""
    return PatentAuditLog.objects.create(
        application=application,
        user_id=user_id,
        actor_role=actor_role,
        action_type=action_type,
        previous_state=previous_state,
        new_state=new_state,
        details=details or {},
        ip_address=ip_address,
    )
