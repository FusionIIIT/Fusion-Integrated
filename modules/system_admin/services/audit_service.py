"""Audit service for System Admin module.

Creates immutable audit entries for all Super Admin operations (BR-SA-025, BR-SA-033, CFR-SA-017).
Audit logs can never be modified or deleted.
"""
from typing import Any
from django.utils import timezone

from modules.system_admin.models import AuditLog


def record_audit_event(
    *,
    actor_user_id: int,
    actor_username: str,
    action: str,
    result: str = "success",
    target_type: str = "",
    target_id: str = "",
    ip_address: str | None = None,
    reason: str = "",
    details: dict[str, Any] | None = None,
) -> AuditLog:
    """Writes an immutable audit log entry.

    Each audit log entry captures timestamp, actor, action, target, IP address,
    result, and context/reason (BR-SA-033).
    """
    entry = AuditLog(
        timestamp=timezone.now(),
        actor_user_id=actor_user_id,
        actor_username=actor_username or f"user_{actor_user_id}",
        action=action,
        result=result,
        target_type=target_type,
        target_id=str(target_id) if target_id else "",
        ip_address=ip_address,
        reason=reason or "",
        details=details or {},
    )
    # Save directly (Model.save enforces immutability on existing PK)
    entry.save()
    return entry
