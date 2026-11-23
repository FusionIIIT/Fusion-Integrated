"""The audit trail (BR-PMS-121, 122; PMS-AFR-207..213): ids and codes only, never content."""
from __future__ import annotations

from modules.pms.models import AuditEntry


def record(actor, action: str, *, application=None, obj=None, frm: str = "", to: str = "",
           details: dict | None = None) -> AuditEntry:
    return AuditEntry.objects.create(
        actor_user_id=getattr(actor, "user_id", None),
        actor_role=(getattr(actor, "active_role", "") or "") if actor else "system",
        action=action,
        application=application,
        object_type=type(obj).__name__ if obj is not None else "",
        object_id=getattr(obj, "pk", None),
        from_state=frm or "",
        to_state=to or "",
        details=details or {},
    )
