"""System configuration parameter management service (CFR-SA-023, BR-SA-035)."""
from __future__ import annotations

from django.db import transaction

from modules.system_admin.constants import AuditAction, AuditResult, PermittedConfigKey
from modules.system_admin.domain import validators
from modules.system_admin.domain.exceptions import ConfigurationBoundaryViolationError
from modules.system_admin.models import SuperAdminAuditLog, SystemParameter


def update_system_parameter(
    key: str, value: str, performed_by_id: int
) -> SystemParameter:
    """Update permitted system-wide parameter within authorized boundary (BR-SA-035)."""
    validators.validate_configuration_key(key, PermittedConfigKey.ALL_KEYS)

    # Validate value constraints
    if key == PermittedConfigKey.BULK_OPERATION_MAX_RECORDS:
        try:
            val_int = int(value)
            if val_int > 1000 or val_int <= 0:
                raise ConfigurationBoundaryViolationError("Bulk max records must be between 1 and 1000 (BR-SA-030).")
        except ValueError as exc:
            raise ConfigurationBoundaryViolationError("Bulk max records must be an integer.") from exc

    with transaction.atomic():
        param, created = SystemParameter.objects.update_or_create(
            key=key,
            defaults={
                "value": str(value),
                "updated_by": performed_by_id,
            },
        )

        SuperAdminAuditLog.objects.create(
            actor_id=performed_by_id,
            actor_username="admin",
            action=AuditAction.CONFIG_UPDATE,
            result=AuditResult.SUCCESS,
            reason=f"Updated parameter '{key}'",
            context_metadata={"key": key, "new_value": str(value)},
        )

    return param
