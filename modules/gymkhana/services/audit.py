"""Append to the audit trail inside the caller's transaction; ids and codes only."""
from __future__ import annotations

from modules.gymkhana.models import AuditEvent


def record(action: str, *, object_type: str, object_id: int, actor=None,
           club_id: int | None = None, **details) -> AuditEvent:
    return AuditEvent.objects.create(
        action=action, object_type=object_type, object_id=object_id,
        actor_user_id=getattr(actor, "user_id", None), club_id=club_id,
        details=details)
