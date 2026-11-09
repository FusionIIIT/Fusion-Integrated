"""Seed default permitted system configuration parameters."""
from django.core.management.base import BaseCommand

from modules.system_admin.constants import PermittedConfigKey
from modules.system_admin.models import SystemParameter

DEFAULTS = [
    (PermittedConfigKey.PASSWORD_MIN_LENGTH, "12", "int", "password"),
    (PermittedConfigKey.PASSWORD_COMPLEXITY_REQUIRED, "true", "bool", "password"),
    (PermittedConfigKey.PASSWORD_ROTATION_DAYS, "90", "int", "password"),
    (PermittedConfigKey.SESSION_INACTIVITY_TIMEOUT_MINUTES, "15", "int", "session"),
    (PermittedConfigKey.ARCHIVAL_MIN_DEACTIVATION_DAYS, "30", "int", "archival"),
    (PermittedConfigKey.ARCHIVAL_REVERSIBLE_WINDOW_DAYS, "30", "int", "archival"),
    (PermittedConfigKey.ARCHIVAL_HISTORICAL_RETENTION_YEARS, "10", "int", "archival"),
    (PermittedConfigKey.ROLE_EXPIRY_REMINDER_LEAD_DAYS, "7", "int", "role"),
    (PermittedConfigKey.ROLE_PREVIOUS_HOLDER_AUDIT_DAYS, "90", "int", "role"),
    (PermittedConfigKey.NOTIFICATION_ENABLE_SMS_ALERTS, "false", "bool", "notification"),
    (PermittedConfigKey.BULK_OPERATION_MAX_RECORDS, "1000", "int", "bulk"),
]


class Command(BaseCommand):
    help = "Seed or synchronize default permitted system parameters."

    def handle(self, *args, **options):
        synced = 0
        for key, val, vtype, category in DEFAULTS:
            _, created = SystemParameter.objects.get_or_create(
                key=key,
                defaults={
                    "value": val,
                    "value_type": vtype,
                    "category": category,
                    "updated_by": 0,
                },
            )
            if created:
                synced += 1
        self.stdout.write(self.style.SUCCESS(f"Synchronized {synced} default system parameters."))
