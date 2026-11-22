"""Read selectors for audit trails, failed logins, and parameters."""
from __future__ import annotations

from datetime import datetime

from modules.system_admin.models.audit import FailedLoginLog, SystemAuditLog
from modules.system_admin.models.configuration import SystemParameter


def list_audit_logs(
    *,
    actor_id: int | None = None,
    action: str | None = None,
    target_id: str | None = None,
    result: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[SystemAuditLog], int]:
    """Filter immutable audit trail (AFR-SA-064, BR-SA-025)."""
    qs = SystemAuditLog.objects.all()

    if actor_id is not None:
        qs = qs.filter(actor_id=actor_id)
    if action:
        qs = qs.filter(action__icontains=action.strip())
    if target_id:
        qs = qs.filter(target_id=target_id.strip())
    if result:
        qs = qs.filter(result=result.strip().lower())
    if start_time:
        qs = qs.filter(timestamp__gte=start_time)
    if end_time:
        qs = qs.filter(timestamp__lte=end_time)

    total = qs.count()
    logs = list(qs[offset : offset + limit])
    return logs, total


def list_failed_logins(
    *, username: str | None = None, limit: int = 50
) -> list[FailedLoginLog]:
    """List recent failed login attempts (BR-SA-034)."""
    qs = FailedLoginLog.objects.all()
    if username:
        qs = qs.filter(username__icontains=username.strip())
    return list(qs[:limit])


def get_system_parameters() -> dict[str, str]:
    """Get all configured system parameters as key-value pairs (BR-SA-035)."""
    params = SystemParameter.objects.all()
    return {p.key: p.value for p in params}
