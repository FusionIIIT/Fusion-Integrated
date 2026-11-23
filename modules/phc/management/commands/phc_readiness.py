"""Print what the PHC module still needs before it can serve every use case."""
from django.core.management.base import BaseCommand, CommandError

from modules.phc import registry


class Command(BaseCommand):
    help = "List unmet PHC prerequisites; exits non-zero when any remain"

    def handle(self, *args, **opts):
        unmet = registry.readiness()
        for line in unmet:
            self.stdout.write(f"- {line}")
        if unmet:
            raise CommandError("PHC is not ready: resolve the items above.")
        self.stdout.write(self.style.SUCCESS("PHC is ready."))
