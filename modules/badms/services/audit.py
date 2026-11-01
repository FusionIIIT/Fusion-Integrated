from modules.badms.models import AuditEvent


def record(actor_id, action, *, object_type="", object_id="", outcome="SUCCESS", details=None):
    return AuditEvent.objects.create(
        actor_id=actor_id,
        action=action,
        object_type=object_type,
        object_id=str(object_id) if object_id else "",
        outcome=outcome,
        details=details or {},
    )
