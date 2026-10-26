"""Name every unmet ELM prerequisite, or say it is ready."""
from django.core.management.base import BaseCommand, CommandError

from modules.elm.registry import readiness
from modules.elm.selectors.config import effective_calendar_version


class Command(BaseCommand):
    help = "Check that ELM can take its first leave application"

    def handle(self, *args, **opts):
        unmet = readiness()
        if effective_calendar_version() is None:
            self.stdout.write(self.style.WARNING(
                "  no published holiday/RH calendar: RH and VL requests will be refused "
                "until the Leave Administrator publishes one"))
        if unmet:
            raise CommandError("ELM is not ready:\n" + "\n".join(f"  - {u}" for u in unmet))
        self.stdout.write(self.style.SUCCESS("ELM is ready"))
