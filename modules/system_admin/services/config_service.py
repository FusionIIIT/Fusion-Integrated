"""System configuration service for System Admin module.

Implements UC-SA-027, AFR-SA-076, AFR-SA-077, BR-SA-035:
Super Admin may configure only the permitted system-wide parameters
(password rotation, session timeout, archival retention periods, bulk limits, etc.).
Denies modifications to academic, financial, and operational module configurations.
"""
from typing import Any
from django.db import transaction

from modules.system_admin.domain import (
    validate_permitted_system_configuration,
)
from modules.system_admin.models import SystemConfiguration
from modules.system_admin.services.audit_service import record_audit_event

DEFAULT_CONFIGURATIONS = {
    "password_rotation_days": 90,
    "session_inactivity_timeout_minutes": 15,
    "deactivation_to_archive_days": 30,
    "reversible_archive_window_days": 180,
    "archive_retention_years": 7,
    "role_expiry_lead_days": 30,
    "previous_holder_audit_days": 30,
    "bulk_operation_limit": 1000,
    "failed_login_alert_threshold": 5,
    "enforce_ip_whitelist": False,
    "ip_whitelist": ["127.0.0.1", "::1"],
    "notification_channels": ["in_system", "email"],
}


def get_all_configurations() -> dict[str, Any]:
    """Returns combined system configurations with defaults."""
    configs = dict(DEFAULT_CONFIGURATIONS)
    db_configs = SystemConfiguration.objects.all()
    for c in db_configs:
        configs[c.key] = c.value
    return configs


def get_configuration_value(key: str, default: Any = None) -> Any:
    cfg = SystemConfiguration.objects.filter(key=key).first()
    if cfg:
        return cfg.value
    return DEFAULT_CONFIGURATIONS.get(key, default)


def update_configuration(
    *,
    key: str,
    value: Any,
    actor_user_id: int,
    actor_username: str,
    description: str = "",
    ip_address: str | None = None,
) -> SystemConfiguration:
    """UC-SA-027: Configure Permitted System Parameters (AFR-SA-076, AFR-SA-077).

    Enforces BR-SA-035: Rejects excluded configuration categories.
    """
    validate_permitted_system_configuration([key])

    with transaction.atomic():
        cfg, created = SystemConfiguration.objects.update_or_create(
            key=key,
            defaults={
                "value": value,
                "description": description or f"System configuration for {key}",
                "updated_by_user_id": actor_user_id,
            },
        )

        record_audit_event(
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            action="config.update",
            result="success",
            target_type="configuration",
            target_id=key,
            ip_address=ip_address,
            reason=f"Updated parameter {key}",
            details={"key": key, "value": value},
        )

    return cfg
