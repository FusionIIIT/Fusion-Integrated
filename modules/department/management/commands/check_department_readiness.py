from django.core.management.base import BaseCommand, CommandError

from modules.department.registry import readiness


class Command(BaseCommand):
    help = "Print every unmet prerequisite of the department module; exit non-zero if any."

    def handle(self, *args, **options):
        unmet = readiness()
        for reason in unmet:
            self.stderr.write(f"  - {reason}")
        if unmet:
            raise CommandError(f"Department module has {len(unmet)} unmet prerequisite(s).")
        self.stdout.write("Department module is ready.")
