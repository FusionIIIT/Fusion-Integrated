from modules.badms.models import AuditEvent


def log_audit_event(
    event_type: str,
    actor,
    target_model: str,
    target_id: int | None = None,
    department: str = "",
    details: dict | None = None,
    ip_address: str | None = None,
) -> AuditEvent:
    user_id = getattr(actor, "user_id", None) or 0
    role = getattr(actor, "active_role", "") or ""
    dept = department or getattr(actor, "department", "") or ""
    return AuditEvent.objects.create(
        event_type=event_type,
        actor_user_id=user_id,
        actor_role=role,
        target_model=target_model,
        target_id=target_id,
        department=dept,
        details=details or {},
        ip_address=ip_address,
    )
