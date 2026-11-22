from modules.badms.models import AuditEvent


def record(*, actor_user_id: int | None, action: str, resource: str,
           resource_id: str = "", outcome: str = "success",
           details: dict | None = None) -> AuditEvent:
    return AuditEvent.objects.create(
        actor_user_id=actor_user_id,
        action=action,
        resource=resource,
        resource_id=resource_id,
        outcome=outcome,
        details=details or {},
    )
