from modules.phc.models import AuditEvent, Notification

def record_audit(entity_type: str, entity_id: int, action: str, actor_user_id: int | None = None, actor_role: str = "", from_status: str = "", to_status: str = "", note: str = "") -> AuditEvent:
    return AuditEvent.objects.create(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        from_status=from_status,
        to_status=to_status,
        note=note,
    )

def notify(recipient_user_id: int, kind: str, message: str, entity_type: str = "", entity_id: int | None = None) -> Notification:
    return Notification.objects.create(
        recipient_user_id=recipient_user_id,
        kind=kind,
        message=message,
        entity_type=entity_type,
        entity_id=entity_id,
    )
