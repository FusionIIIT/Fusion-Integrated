"""Audit service for recording immutable SPACS events.

Enforces:
- CFR-SPACS-016 (Audit Trail)
- AFR-SPACS-049, AFR-SPACS-050
- BR-SPACS-021
"""
from __future__ import annotations

import logging
from typing import Any
from modules.spacs.models import SpacsAuditLog

log = logging.getLogger("fusion.spacs.audit")


def record_audit_event(
    action: str,
    entity_type: str,
    entity_id: str | int,
    actor_user_id: int | None = None,
    actor_role: str = "",
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> SpacsAuditLog:
    """Appends an immutable audit event record."""
    try:
        entry = SpacsAuditLog.objects.create(
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            details=details or {},
            ip_address=ip_address,
        )
        log.info(
            "spacs.audit action=%s entity=%s#%s actor=%s",
            action, entity_type, entity_id, actor_user_id
        )
        return entry
    except Exception as exc:
        log.error("spacs.audit.failed error=%s action=%s", exc, action)
        raise
