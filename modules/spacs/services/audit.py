"""SPACS Audit and Notification Services."""

from ..models import SpacsAuditLog, SpacsNotification
from ..domain.rules import should_notify_event


def log_action(
    event_type: str,
    entity_type: str,
    entity_id: str,
    actor_user_id: int,
    details: dict | None = None,
) -> SpacsAuditLog:
    """Create an append-only audit trail record."""
    return SpacsAuditLog.objects.create(
        event_type=event_type,
        entity_type=entity_type,
        entity_id=str(entity_id),
        actor_user_id=actor_user_id,
        details=details or {},
    )


def notify_user(
    recipient_user_id: int,
    event_type: str,
    title: str,
    message: str,
) -> SpacsNotification | None:
    """Send an in-dashboard notification if the event is significant."""
    if not should_notify_event(event_type):
        return None
    return SpacsNotification.objects.create(
        recipient_user_id=recipient_user_id,
        event_type=event_type,
        title=title,
        message=message,
    )
