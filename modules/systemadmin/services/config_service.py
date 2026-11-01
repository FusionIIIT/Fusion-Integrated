"""System Parameter Configuration Service for System Admin Control Plane.

Implements configuration of permitted system-wide parameters while strictly
enforcing the configuration boundary against operational, academic, and financial
settings conforming to BR-SA-035, AFR-SA-076, and AFR-SA-077.
"""
from typing import Any
from django.db import transaction

from modules.systemadmin.models.config import SystemAdminConfig
from modules.systemadmin.services.audit_service import AuditService
from modules.systemadmin.services.security_service import SecurityService


class ConfigurationError(Exception):
    def __init__(self, message: str, code: str = "config_error"):
        super().__init__(message)
        self.code = code
        self.message = message


PERMITTED_CONFIG_KEYS = {
    "password_min_length": {"type": int, "category": "security", "is_critical": False, "min": 6, "max": 32},
    "password_require_uppercase": {"type": bool, "category": "security", "is_critical": False},
    "password_require_lowercase": {"type": bool, "category": "security", "is_critical": False},
    "password_require_number": {"type": bool, "category": "security", "is_critical": False},
    "password_require_special": {"type": bool, "category": "security", "is_critical": False},
    "session_inactivity_timeout_minutes": {"type": int, "category": "security", "is_critical": False, "min": 5, "max": 240},
    "deactivation_to_archive_interval_days": {"type": int, "category": "archival", "is_critical": False, "min": 1, "max": 365},
    "archival_reversible_window_days": {"type": int, "category": "archival", "is_critical": True, "min": 1, "max": 365},
    "historical_data_retention_years": {"type": int, "category": "archival", "is_critical": True, "min": 1, "max": 25},
    "role_expiry_reminder_lead_days": {"type": int, "category": "role_lifecycle", "is_critical": False, "min": 1, "max": 180},
    "previous_holder_audit_period_days": {"type": int, "category": "role_lifecycle", "is_critical": False, "min": 1, "max": 365},
    "password_rotation_interval_days": {"type": int, "category": "security", "is_critical": False, "min": 15, "max": 365},
    "bulk_operation_limit": {"type": int, "category": "bulk", "is_critical": True, "min": 1, "max": 1000},
    "notification_email_enabled": {"type": bool, "category": "notification", "is_critical": False},
    "notification_in_system_enabled": {"type": bool, "category": "notification", "is_critical": False},
    "notification_sms_enabled": {"type": bool, "category": "notification", "is_critical": False},
    "ip_whitelist_enabled": {"type": bool, "category": "security", "is_critical": True},
    "ip_whitelist": {"type": list, "category": "security", "is_critical": True},
}

DEFAULT_CONFIG_VALUES = {
    "password_min_length": 8,
    "password_require_uppercase": True,
    "password_require_lowercase": True,
    "password_require_number": True,
    "password_require_special": True,
    "session_inactivity_timeout_minutes": 30,
    "deactivation_to_archive_interval_days": 30,
    "archival_reversible_window_days": 90,
    "historical_data_retention_years": 7,
    "role_expiry_reminder_lead_days": 30,
    "previous_holder_audit_period_days": 30,
    "password_rotation_interval_days": 90,
    "bulk_operation_limit": 1000,
    "notification_email_enabled": True,
    "notification_in_system_enabled": True,
    "notification_sms_enabled": False,
    "ip_whitelist_enabled": False,
    "ip_whitelist": ["127.0.0.1", "::1"],
}


class ConfigService:
    @classmethod
    def get_value(cls, key: str, default: Any = None) -> Any:
        cfg = SystemAdminConfig.objects.filter(key=key).first()
        if cfg:
            return cfg.value
        return DEFAULT_CONFIG_VALUES.get(key, default)

    @classmethod
    def get_all_configurations(cls) -> list[dict[str, Any]]:
        db_configs = {c.key: c for c in SystemAdminConfig.objects.all()}
        result = []
        for key, meta in PERMITTED_CONFIG_KEYS.items():
            db_item = db_configs.get(key)
            val = db_item.value if db_item else DEFAULT_CONFIG_VALUES.get(key)
            result.append({
                "key": key,
                "value": val,
                "category": meta["category"],
                "is_critical": meta.get("is_critical", False),
                "type": meta["type"].__name__,
                "description": db_item.description if db_item else "",
                "updated_by": db_item.updated_by if db_item else "system",
            })
        return result

    @classmethod
    @transaction.atomic
    def update_configuration(
        cls,
        key: str,
        value: Any,
        confirmation_token: str = "",
        actor_username: str = "superadmin",
        ip_address: str | None = None,
    ) -> SystemAdminConfig:
        """Update a permitted system parameter enforcing boundaries (BR-SA-035, AFR-SA-076, AFR-SA-077)."""
        key = key.strip()

        # BR-SA-035 & AFR-SA-077: Prohibited categories
        prohibited_keywords = ["academic", "calendar", "finance", "fee", "workflow", "grade", "syllabus"]
        if any(keyword in key.lower() for keyword in prohibited_keywords) or key not in PERMITTED_CONFIG_KEYS:
            raise ConfigurationError(
                f"Configuration key '{key}' is outside the Super Admin control plane. "
                "Super Admin is prohibited from modifying academic, financial, or operational module settings.",
                code="prohibited_configuration_boundary"
            )

        meta = PERMITTED_CONFIG_KEYS[key]

        # Type validation & range bounds
        expected_type = meta["type"]
        if expected_type == int:
            try:
                value = int(value)
            except (ValueError, TypeError):
                raise ConfigurationError(f"Value for '{key}' must be an integer.", code="invalid_type")
            if "min" in meta and value < meta["min"]:
                raise ConfigurationError(f"Value for '{key}' cannot be less than {meta['min']}.", code="value_out_of_bounds")
            if "max" in meta and value > meta["max"]:
                raise ConfigurationError(f"Value for '{key}' cannot exceed {meta['max']}.", code="value_out_of_bounds")
        elif expected_type == bool:
            if not isinstance(value, bool):
                value = str(value).lower() in ("true", "1", "yes")
        elif expected_type == list:
            if not isinstance(value, list):
                raise ConfigurationError(f"Value for '{key}' must be a list.", code="invalid_type")

        # BR-SA-029: Reauthentication for critical configuration changes
        if meta.get("is_critical", False):
            SecurityService.reauthenticate_critical_operation(actor_username, confirmation_token)

        cfg, _ = SystemAdminConfig.objects.update_or_create(
            key=key,
            defaults={
                "value": value,
                "category": meta["category"],
                "is_critical": meta.get("is_critical", False),
                "updated_by": actor_username,
            }
        )

        AuditService.log_action(
            actor_username=actor_username,
            action="CONFIG_UPDATE",
            result="SUCCESS",
            ip_address=ip_address,
            reason_or_context=f"Updated parameter '{key}'",
            metadata={"key": key, "new_value": value},
        )

        return cfg


get_value = ConfigService.get_value
get_all_configurations = ConfigService.get_all_configurations
update_configuration = ConfigService.update_configuration
