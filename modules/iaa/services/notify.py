"""Dashboard notifications (BR-504); recipients stay inside role/ownership scope."""
from __future__ import annotations

from modules.iaa.models import Notification


def to_user(user_id: int | None, kind: str, message: str, entity: str, entity_id: int) -> None:
    if user_id is None:
        return
    Notification.objects.create(recipient_user_id=user_id, kind=kind, message=message[:300],
                                entity=entity, entity_id=entity_id)


def to_role(role: str, kind: str, message: str, entity: str, entity_id: int) -> None:
    if not role:
        return
    Notification.objects.create(recipient_role=role, kind=kind, message=message[:300],
                                entity=entity, entity_id=entity_id)
