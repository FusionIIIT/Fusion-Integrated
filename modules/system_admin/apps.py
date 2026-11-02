from django.apps import AppConfig
from django.core.checks import Error, Warning as CheckWarning, register


def check_system_admin_settings(app_configs, **kwargs):
    """System checks for system_admin module settings and thresholds."""
    from django.conf import settings

    errors = []
    config = getattr(settings, "SYSTEM_ADMIN_CONFIG", {})

    max_bulk = config.get("MAX_BULK_SIZE", 1000)
    if max_bulk > 1000:
        errors.append(
            Error(
                f"SYSTEM_ADMIN_CONFIG['MAX_BULK_SIZE'] is {max_bulk}, exceeding maximum limit of 1000 (BR-SA-030).",
                id="system_admin.E001",
            )
        )

    alert_thresh = config.get("FAILED_LOGIN_ALERT_THRESHOLD", 5)
    if alert_thresh != 5:
        errors.append(
            CheckWarning(
                f"SYSTEM_ADMIN_CONFIG['FAILED_LOGIN_ALERT_THRESHOLD'] is set to {alert_thresh}; standard policy baseline is 5 (BR-SA-024).",
                id="system_admin.W001",
            )
        )

    return errors


class SystemAdminConfig(AppConfig):
    name = "modules.system_admin"
    label = "system_admin"
    verbose_name = "System Administration Control Plane"

    def ready(self):
        register(check_system_admin_settings)
