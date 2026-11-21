"""Audit logs and administrative activity selectors for system_admin."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from django.db.models import Q

from modules.system_admin.models import SuperAdminAuditLog, UserActivityLog


def query_audit_logs(
    *,
    actor_id: Optional[int] = None,
    target_user_id: Optional[int] = None,
    action: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
) -> Tuple[Sequence[SuperAdminAuditLog], int]:
    """Search and filter permanent audit trail records (CFR-SA-018, BR-SA-025)."""
    qs = SuperAdminAuditLog.objects.all().order_by("-timestamp")
    if actor_id is not None:
        qs = qs.filter(actor_id=actor_id)
    if target_user_id is not None:
        qs = qs.filter(target_user_id=target_user_id)
    if action:
        qs = qs.filter(action=action)
    if date_from:
        qs = qs.filter(timestamp__gte=date_from)
    if date_to:
        qs = qs.filter(timestamp__lte=date_to)

    capped_limit = min(limit, 500)
    total = qs.count()
    return list(qs[offset : offset + capped_limit]), total


def generate_audit_report_dataset(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Format audit trail records into export-ready rows for CSV/JSON (UC-SA-025)."""
    logs, _ = query_audit_logs(
        actor_id=filters.get("actor_id"),
        target_user_id=filters.get("target_user_id"),
        action=filters.get("action"),
        date_from=filters.get("date_from"),
        date_to=filters.get("date_to"),
        limit=500,
    )
    rows = []
    for log in logs:
        rows.append(
            {
                "id": log.id,
                "timestamp": log.timestamp.isoformat(),
                "actor_id": log.actor_id,
                "actor_username": log.actor_username,
                "action": log.action,
                "target_user_id": log.target_user_id or "",
                "target_role_code": log.target_role_code or "",
                "ip_address": log.ip_address or "",
                "result": log.result,
                "reason": log.reason,
            }
        )
    return rows


def query_user_activity_logs(user_id: int, limit: int = 50) -> Sequence[UserActivityLog]:
    """Retrieve recent activity logs for a user."""
    return list(
        UserActivityLog.objects.filter(user_id=user_id)
        .order_by("-timestamp")[:limit]
    )
