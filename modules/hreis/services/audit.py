"""Audit logging service (BR-HR-025, AFR-083 to AFR-089)."""
from __future__ import annotations

from typing import Any

from modules.hreis.models import HrAuditLog


def log_hr_action(
    *,
    actor_id: int,
    actor_username: str,
    actor_role: str,
    action: str,
    entity_type: str,
    entity_id: str | int,
    details: dict[str, Any] | None = None,
    ip_address: str = "",
) -> HrAuditLog:
    """Create an immutable audit log record for an HR transaction."""
    return HrAuditLog.objects.create(
        actor_id=actor_id,
        actor_username=actor_username or f"user_{actor_id}",
        actor_role=actor_role or "employee",
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        details=details or {},
        ip_address=ip_address,
    )
