"""Check whether RSPC module prerequisites and tables are ready."""

from __future__ import annotations

import sys

from django.core.management.base import BaseCommand

from modules.rspc.registry import readiness


class Command(BaseCommand):
    help = "Check RSPC module readiness."

    def handle(self, *args, **options) -> None:
        self.stdout.write("Checking RSPC module readiness...")
        unmet = readiness()
        if unmet:
            self.stdout.write(self.style.ERROR(f"RSPC is NOT ready ({len(unmet)} issues):"))
            for issue in unmet:
                self.stdout.write(self.style.WARNING(f"  - {issue}"))
            sys.exit(1)
        self.stdout.write(self.style.SUCCESS("RSPC module is ready."))
