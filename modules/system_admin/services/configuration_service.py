"""Permitted system parameters configuration service."""
from __future__ import annotations

from typing import Any

from django.db import transaction

from modules.system_admin.domain.rules import validate_system_parameters
from modules.system_admin.models.audit import SystemAuditLog
from modules.system_admin.models.configuration import SystemParameter


@transaction.atomic
def update_system_parameters(
    *,
    params: dict[str, Any],
    actor_id: int = 1,
    ip_address: str | None = None,
) -> dict[str, str]:
    """Validate and update permitted system parameters (BR-SA-027, 030, 035)."""
    typed_params: dict[str, Any] = {}
    int_keys = {"bulk_operation_limit", "session_timeout_minutes", "archival_retention_years"}
    for k, v in params.items():
        if k in int_keys:
            try:
                typed_params[k] = int(v)
            except (ValueError, TypeError):
                typed_params[k] = v
        else:
            typed_params[k] = v

    validate_system_parameters(typed_params)

    updated: dict[str, str] = {}
    for key, value in params.items():
        str_val = str(value)
        SystemParameter.objects.update_or_create(
            key=key,
            defaults={
                "label": key.replace("_", " ").title(),
                "value": str_val,
                "updated_by": actor_id,
            },
        )
        updated[key] = str_val

    SystemAuditLog.objects.create(
        actor_id=actor_id,
        action="system_admin.config.change",
        target_id="system_parameters",
        ip_address=ip_address,
        result="success",
        context={"updated_keys": list(params.keys())},
    )

    return updated
