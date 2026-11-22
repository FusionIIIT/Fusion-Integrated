"""Immutable audit logging and security monitoring service."""
from __future__ import annotations

from typing import Any

from modules.system_admin.models.audit import (
    AdminSessionLog,
    FailedLoginLog,
    SystemAuditLog,
)


def record_audit_event(
    *,
    actor_id: int,
    action: str,
    target_id: str = "",
    ip_address: str | None = None,
    result: str = "success",
    context: dict[str, Any] | None = None,
) -> SystemAuditLog:
    """Record an immutable audit log entry (BR-SA-025, BR-SA-033)."""
    return SystemAuditLog.objects.create(
        actor_id=actor_id,
        action=action,
        target_id=target_id,
        ip_address=ip_address,
        result=result,
        context=context or {},
    )


def record_failed_login(
    *,
    username: str,
    ip_address: str | None = None,
    reason: str = "",
) -> FailedLoginLog:
    """Record a failed login attempt for brute force and security monitoring (BR-SA-034)."""
    return FailedLoginLog.objects.create(
        username=username,
        ip_address=ip_address,
        reason=reason,
    )


def record_admin_session(
    *,
    user_id: int,
    session_key: str,
    ip_address: str | None = None,
    user_agent: str = "",
) -> AdminSessionLog:
    """Track an active administrative session."""
    return AdminSessionLog.objects.create(
        user_id=user_id,
        session_key=session_key,
        ip_address=ip_address,
        user_agent=user_agent,
        is_active=True,
    )
