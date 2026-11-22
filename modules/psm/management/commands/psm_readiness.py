# Print unmet PSM operational prerequisites and exit non-zero if any exist (Step 7.5).
from django.core.management.base import BaseCommand, CommandError

from modules.psm.registry import readiness


class Command(BaseCommand):
    help = "Verify PSM operational readiness and list any unmet prerequisites."

    def handle(self, *args, **options):
        missing = readiness()
        if missing:
            for item in missing:
                self.stderr.write(f"NOT READY: {item}")
            raise CommandError(f"{len(missing)} unmet PSM prerequisite(s).")
        self.stdout.write(self.style.SUCCESS("PSM module is ready."))
