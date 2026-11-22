"""Immutable audit logging service."""

from modules.superadmin.models import AuditLogRecord


def log_audit_event(
    *,
    event_type: str,
    actor_user_id: int,
    target_entity: str,
    target_id: str,
    ip_address: str | None = None,
    action_details: dict | None = None,
) -> AuditLogRecord:
    # BR-SA-025 & BR-SA-033: Write append-only immutable audit log entry.
    return AuditLogRecord.objects.create(
        event_type=event_type,
        actor_user_id=actor_user_id,
        target_entity=target_entity,
        target_id=str(target_id),
        ip_address=ip_address,
        action_details=action_details or {},
        is_immutable=True,
    )
