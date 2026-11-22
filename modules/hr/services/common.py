from __future__ import annotations

from modules.hr.models import AuditEvent


def audit(
    *, actor, entity_type: str, entity_id: int, action: str, details: dict | None = None
) -> AuditEvent:
    return AuditEvent.objects.create(
        entity_type=entity_type,
        entity_id=entity_id,
        actor_user_id=getattr(actor, "user_id", None),
        action=action,
        details=details or {},
    )
