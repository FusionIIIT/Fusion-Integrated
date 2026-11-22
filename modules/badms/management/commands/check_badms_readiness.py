from django.core.management.base import BaseCommand, CommandError

from modules.badms.registry import readiness


class Command(BaseCommand):
    help = "Check BADMS production prerequisites and explain every unmet item"

    def handle(self, *args, **options):
        unmet = readiness()
        if unmet:
            self.stderr.write(self.style.ERROR("BADMS is not ready:"))
            for item in unmet:
                self.stderr.write(f"- {item}")
            raise CommandError(f"{len(unmet)} BADMS readiness prerequisite(s) unmet.")
        self.stdout.write(self.style.SUCCESS("BADMS prerequisites are configured."))
