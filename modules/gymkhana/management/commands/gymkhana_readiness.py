"""Print what the Gymkhana module still needs before it can be used; non-zero if anything."""
from django.core.management.base import BaseCommand, CommandError

from modules.gymkhana.registry import readiness


class Command(BaseCommand):
    help = "Report Gymkhana's unmet prerequisites"

    def handle(self, *args, **opts):
        unmet = readiness()
        if unmet:
            for reason in unmet:
                self.stderr.write(f"  - {reason}")
            raise CommandError(f"gymkhana is not ready: {len(unmet)} prerequisite(s) unmet.")
        self.stdout.write(self.style.SUCCESS("gymkhana is ready."))
