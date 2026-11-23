from django.core.management.base import BaseCommand, CommandError

from modules.accesscontrol.contracts import active_module_codes
from modules.department.registry import readiness


class Command(BaseCommand):
    help = "Check the Department schema, directory configuration and module registration."

    def handle(self, *args, **options):
        missing = readiness()
        if not missing and "department" not in active_module_codes():
            missing.append("Run manage.py seed_modules to activate Department.")
        if missing:
            raise CommandError("\n".join(missing))
        self.stdout.write(self.style.SUCCESS("Department is ready."))
