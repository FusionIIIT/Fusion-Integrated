"""Append-only audit trail (VMS-CFR-005). Every state change calls record()."""
from __future__ import annotations

from modules.vms.models import AuditLog


def _actor_fields(actor) -> tuple[int | None, str]:
    """`actor` is a Principal, an int user id, or None for the system."""
    if actor is None:
        return None, "system"
    if isinstance(actor, int):
        return actor, ""
    if getattr(actor, "kind", None) == "visitor":
        return None, "visitor"
    return getattr(actor, "user_id", None), getattr(actor, "active_role", None) or ""


def record(*, actor, action: str, entity, detail: dict | None = None) -> AuditLog:
    """Write one AuditLog row. `entity` is a saved model instance."""
    if entity.pk is None:
        raise ValueError("audit.record needs a saved entity")
    user_id, role = _actor_fields(actor)
    return AuditLog.objects.create(
        actor_user_id=user_id, actor_role=role, action=action,
        entity_type=entity._meta.model_name, entity_id=str(entity.pk),
        detail=detail or {})
