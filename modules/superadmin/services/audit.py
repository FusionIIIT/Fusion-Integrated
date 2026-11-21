from __future__ import annotations

from typing import Any

from modules.superadmin.models.audit import SuperAdminAuditLog


def record_audit_event(
    *,
    actor_id: int,
    actor_username: str,
    actor_role: str,
    action: str,
    target_id: str = "",
    target_type: str = "",
    result: str = "SUCCESS",
    ip_address: str | None = None,
    user_agent: str = "",
    reason: str = "",
    context_metadata: dict[str, Any] | None = None,
) -> SuperAdminAuditLog:
    # Retained permanently, strictly immutable compliance audit entry
    entry = SuperAdminAuditLog(
        actor_id=actor_id,
        actor_username=actor_username,
        actor_role=actor_role,
        action=action,
        target_id=target_id,
        target_type=target_type,
        result=result,
        ip_address=ip_address,
        user_agent=user_agent,
        reason=reason,
        context_metadata=context_metadata or {},
    )
    # entry.pk is None here — the model guard only blocks updates (pk is not None).
    entry.save()
    return entry
