"""Management command to manually process expired role assignments."""
from django.core.management.base import BaseCommand

from modules.system_admin.services.role_service import process_role_expiries


class Command(BaseCommand):
    help = "Process expired role assignments and transition them to expired status (BR-SA-009)"

    def handle(self, *args, **options):
        count = process_role_expiries()
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully processed {count} expired role assignments."
            )
        )
