"""Report prerequisites that keep the PMS module inactive."""

from django.core.management.base import BaseCommand, CommandError

from modules.pms.registry import readiness


class Command(BaseCommand):
    help = "Report unmet prerequisites for activating the PMS module."

    def handle(self, *args, **options):
        unmet = readiness()
        if unmet:
            self.stdout.write(self.style.ERROR("PMS is not ready:"))
            for prerequisite in unmet:
                self.stdout.write(f"- {prerequisite}")
            raise CommandError(f"{len(unmet)} PMS prerequisite(s) remain unmet.")
        self.stdout.write(self.style.SUCCESS("PMS is ready."))
