from django.core.management.base import BaseCommand, CommandError

from modules.department.registry import readiness
from modules.department.selectors.readiness import role_warnings


class Command(BaseCommand):
    help = "Print unmet prerequisites (exit non-zero) and every vacant or ending department role."

    def handle(self, *args, **options):
        unmet = readiness()
        for reason in unmet:
            self.stderr.write(f"  - {reason}")
        if unmet:
            raise CommandError(f"Department module has {len(unmet)} unmet prerequisite(s).")
        for warning in role_warnings():
            self.stdout.write(self.style.WARNING(f"  ! {warning['message']}"))
        self.stdout.write("Department module is ready.")
