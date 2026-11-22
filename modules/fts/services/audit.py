"""Audit logging and integrity services for FTS."""
from __future__ import annotations

from typing import Any

from modules.fts.models.audit import FileAuditLog
from modules.fts.models.files import File
from modules.fts.models.movements import FileMovement


def record_audit(
    *,
    file_id: int,
    action: str,
    actor_user_id: int,
    actor_username: str,
    actor_role: str,
    details: dict[str, Any] | None = None,
) -> FileAuditLog:
    """Creates an immutable audit log entry."""
    return FileAuditLog.objects.create(
        file_id=file_id,
        action=action,
        actor_user_id=actor_user_id,
        actor_username=actor_username,
        actor_role=actor_role,
        details=details or {},
    )


def verify_all_files_audit_integrity() -> bool:
    """Verifies that sequence numbers and timestamps are monotonically strictly increasing."""
    file_ids = File.objects.values_list("id", flat=True)
    for fid in file_ids:
        movements = list(FileMovement.objects.filter(file_id=fid).order_by("sequence"))
        for i in range(len(movements)):
            if movements[i].sequence != i + 1:
                return False
            if i > 0 and movements[i].created_at < movements[i - 1].created_at:
                return False
    return True
