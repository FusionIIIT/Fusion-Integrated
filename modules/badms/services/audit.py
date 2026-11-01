"""Audit logging service for BADMS."""
from __future__ import annotations

from typing import Any
from modules.badms.models import BadmsAuditLog


def record_audit(
    *,
    actor_user_id: int,
    action: str,
    target_type: str,
    target_id: str | int,
    actor_role: str = "",
    outcome: str = "success",
    details: dict[str, Any] | None = None,
) -> BadmsAuditLog:
    """Record an immutable audit event."""
    return BadmsAuditLog.objects.create(
        actor_user_id=actor_user_id,
        actor_role=actor_role or "",
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        outcome=outcome,
        details=details or {},
    )
