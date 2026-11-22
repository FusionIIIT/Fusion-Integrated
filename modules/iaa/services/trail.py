"""The audit trail writer (BR-503): identity, active role, action and resulting status."""
from __future__ import annotations

from modules.iaa.models import TrailEntry
from modules.iaa.services.authz import role_of

SYSTEM_ROLE = "system"


def log(entity: str, entity_id: int, action: str, *, actor=None, frm: str = "",
        to: str = "", remarks: str = "") -> TrailEntry:
    return TrailEntry.objects.create(
        entity=entity, entity_id=entity_id, action=action, from_status=frm, to_status=to,
        actor_user_id=getattr(actor, "user_id", None),
        actor_role=role_of(actor) if actor is not None else SYSTEM_ROLE,
        remarks=remarks)
