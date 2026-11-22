"""Seed initial system configuration policies for Super Admin."""

from django.core.management.base import BaseCommand
from django.utils import timezone

from modules.superadmin.models import SystemParameterPolicy

DEFAULT_POLICIES = [
    (
        "REVERSIBILITY_WINDOW_DAYS",
        {"value": 90},
        "Reversibility window in days for archived user accounts (BW-SA-08).",
    ),
    (
        "MIN_DEACTIVATION_ARCHIVE_DAYS",
        {"value": 30},
        "Minimum interval in days between deactivation and archival (BR-SA-04).",
    ),
    (
        "FAILED_LOGIN_THRESHOLD",
        {"value": 5},
        "Threshold for consecutive failed logins before security alert (BR-SA-024).",
    ),
    (
        "BULK_OPERATION_MAX_LIMIT",
        {"value": 500},
        "Maximum batch limit for bulk user creation and status updates (BR-SA-030).",
    ),
]


class Command(BaseCommand):
    help = "Seed baseline institutional system parameter policies for Super Admin"

    def handle(self, *args, **options):
        now = timezone.now()
        created_count = 0
        for key, val, _desc in DEFAULT_POLICIES:
            _, created = SystemParameterPolicy.objects.get_or_create(
                parameter_key=key,
                version=1,
                defaults={
                    "parameter_value": val,
                    "effective_from": now,
                    "is_active": True,
                    "updated_by_user_id": 1,
                },
            )
            if created:
                created_count += 1
                self.stdout.write(f"  seeded policy parameter {key}")
        self.stdout.write(
            self.style.SUCCESS(f"Super Admin policies seeded ({created_count} created)")
        )
