"""Print what the placement module still needs before it can be switched on."""
from django.core.management.base import BaseCommand, CommandError

from modules.placement import registry


class Command(BaseCommand):
    help = "List unmet prerequisites; exit non-zero while any remain."

    def handle(self, *args, **opts):
        unmet = registry.readiness()
        for reason in unmet:
            self.stdout.write(f"  {reason}")
        if unmet:
            raise CommandError(f"{len(unmet)} prerequisite(s) unmet.")
        self.stdout.write(self.style.SUCCESS("placement is ready."))
