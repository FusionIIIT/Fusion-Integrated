"""Audit service for File Tracking System (BR-FTS-011)."""

from typing import Any

from modules.filetracking.models import FileAuditLog


def record_audit(
    action: str,
    actor_user_id: int,
    actor_designation: str,
    file_id: int | None = None,
    payload: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> FileAuditLog:
    """Record an immutable chronological audit trail entry."""
    return FileAuditLog.objects.create(
        file_id=file_id,
        action=action,
        actor_user_id=actor_user_id,
        actor_designation=actor_designation,
        payload=payload or {},
        ip_address=ip_address,
    )
