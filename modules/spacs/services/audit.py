"""Audit log service for SPACS actions (CFR-SPACS-016, BR-SPACS-021)."""
from __future__ import annotations

from typing import Any

from modules.spacs.models import SpacsAuditLog


def record_audit_event(
    *,
    actor_user_id: int | None,
    actor_role: str = "",
    action: str,
    entity_type: str,
    entity_id: str,
    details: dict[str, Any] | None = None,
    ip_address: str = "",
) -> SpacsAuditLog:
    """Creates a timestamped, append-only audit event."""
    return SpacsAuditLog.objects.create(
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        details=details or {},
        ip_address=ip_address,
    )
