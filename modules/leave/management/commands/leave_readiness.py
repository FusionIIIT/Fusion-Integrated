"""Name every unmet prerequisite; exit non-zero while any remains, so a deploy can gate on it."""
from django.core.management.base import BaseCommand, CommandError

from modules.leave.services import readiness


class Command(BaseCommand):
    help = "Report what Leave still needs before it can be switched on"

    def handle(self, *args, **options):
        for warning in readiness.warnings():
            self.stdout.write(self.style.WARNING(f"  warning: {warning}"))
        unmet = readiness.unmet()
        if unmet:
            raise CommandError("Leave is not ready:\n" + "\n".join(f"  - {u}" for u in unmet))
        self.stdout.write(self.style.SUCCESS("Leave is ready"))
