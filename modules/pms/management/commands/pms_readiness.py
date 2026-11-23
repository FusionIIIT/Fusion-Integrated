from django.core.management.base import BaseCommand, CommandError

from modules.pms import registry
from modules.pms.services.policy import setup_gaps


class Command(BaseCommand):
    help = "Say whether PMS can run here, and what PCC_ADMIN still has to configure."

    def handle(self, *args, **opts):
        unmet = registry.readiness()
        gaps = setup_gaps()
        for line in gaps:
            self.stdout.write(f"  configure: {line}")
        if unmet:
            for line in unmet:
                self.stderr.write(f"  unmet: {line}")
            raise CommandError(f"PMS is not ready: {len(unmet)} prerequisite(s) unmet.")
        self.stdout.write(self.style.SUCCESS(
            f"PMS is ready. {len(gaps)} setting(s) still to configure in the app."))
