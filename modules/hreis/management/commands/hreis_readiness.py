"""List unmet HR-EIS prerequisites; fail when the module is not ready."""

from django.core.management.base import BaseCommand, CommandError

from modules.hreis.registry import readiness


class Command(BaseCommand):
    help = "Check required institutional HR-EIS policy configuration."

    def handle(self, *args, **options):
        missing = readiness()
        if missing:
            for item in missing:
                self.stderr.write(f"  - {item}")
            raise CommandError(f"HR-EIS is not ready: {len(missing)} prerequisite(s) unmet.")
        self.stdout.write(self.style.SUCCESS("HR-EIS policy readiness: all configured."))
