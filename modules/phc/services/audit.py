"""Append-only audit entries for sensitive PHC actions (PHC-BR-09)."""
from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

from modules.phc.models import AuditLog


def json_safe(value):
    """Return a JSON-serializable copy of an audit detail value."""
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    if isinstance(value, (date, datetime, time, Decimal)):
        return str(value)
    return value


def record(actor, action: str, target_type: str, target_id: int,
           detail=None) -> AuditLog:
    """Append one audit row; callers invoke this inside their transaction."""
    return AuditLog.objects.create(
        actor=getattr(actor, "user_id", None),
        actor_role=getattr(actor, "active_role", "") or "",
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=json_safe(detail or {}),
    )
