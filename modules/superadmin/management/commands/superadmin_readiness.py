"""Readiness check command for Super Admin."""

from django.core.management.base import BaseCommand

from modules.superadmin.registry import readiness


class Command(BaseCommand):
    help = "Verify readiness of Super Admin module prerequisites"

    def handle(self, *args, **options):
        unmet = readiness()
        if unmet:
            self.stdout.write(
                self.style.WARNING(f"Super Admin has {len(unmet)} unmet prerequisite(s):")
            )
            for item in unmet:
                self.stdout.write(self.style.WARNING(f"  - {item}"))
            return
        self.stdout.write(self.style.SUCCESS("Super Admin module is ready."))
