"""Check Gymkhana module prerequisites and readiness.

    manage.py gymkhana_readiness
"""
from django.core.management.base import BaseCommand, CommandError

from modules.gymkhana.registry import readiness


class Command(BaseCommand):
    help = "Check Gymkhana module prerequisites and readiness"

    def handle(self, *args, **options):
        unmet = readiness()
        if unmet:
            self.stdout.write(self.style.ERROR("Gymkhana prerequisites not met:"))
            for item in unmet:
                self.stdout.write(f"  - {item}")
            raise CommandError("Gymkhana is not ready to serve traffic.")
        self.stdout.write(self.style.SUCCESS("Gymkhana is ready."))
