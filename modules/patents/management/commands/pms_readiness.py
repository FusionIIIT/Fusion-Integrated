"""Check whether the patents module is ready for production operation (Step 7.5)."""
from django.core.management.base import BaseCommand

from modules.patents.registry import readiness


class Command(BaseCommand):
    help = "Check patents module deployment readiness prerequisites."

    def handle(self, *args, **options):
        unmet = readiness()
        if unmet:
            self.stdout.write(self.style.WARNING("Patents module is NOT ready:"))
            for item in unmet:
                self.stdout.write(self.style.WARNING(f"  - {item}"))
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS("Patents module is ready for operation."))
