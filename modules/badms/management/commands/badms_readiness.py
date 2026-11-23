from django.core.management.base import BaseCommand

from modules.badms.registry import readiness


class Command(BaseCommand):
    help = "Check BADMS operational prerequisites and readiness."

    def handle(self, *args, **options):
        unmet = readiness()
        if unmet:
            for item in unmet:
                self.stderr.write(self.style.ERROR(f"Unmet prerequisite: {item}"))
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS("BADMS is fully ready and operational."))
