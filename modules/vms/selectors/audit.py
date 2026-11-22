"""Read-only selectors for audit trails."""

from __future__ import annotations

from django.db.models import QuerySet

from modules.vms.models import GateCheckLog


def list_audit_logs(
    pass_id: int | None = None,
    action: str | None = None,
    is_override: bool | None = None,
) -> QuerySet[GateCheckLog]:
    qs = GateCheckLog.objects.select_related("pass_record", "pass_record__visit_request").all()
    if pass_id is not None:
        qs = qs.filter(pass_record_id=pass_id)
    if action:
        qs = qs.filter(action=action)
    if is_override is not None:
        qs = qs.filter(is_override=is_override)
    return qs.order_by("-timestamp")
