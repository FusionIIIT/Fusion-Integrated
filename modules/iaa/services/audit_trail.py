"""Audit trail service enforcing complete logging and role integrity."""

from typing import Any

from modules.iaa.models import AuditLogEntry


def record_audit_log(
    user_id: int,
    acting_role: str,
    action: str,
    target_type: str,
    target_id: int,
    resulting_status: str = "",
    details: dict[str, Any] | None = None,
) -> AuditLogEntry:
    return AuditLogEntry.objects.create(
        user_id=user_id,
        acting_role=acting_role or "unknown",
        action=action,
        target_type=target_type,
        target_id=target_id,
        resulting_status=resulting_status,
        details=details or {},
    )
