from django.core.management.base import BaseCommand, CommandError

from modules.lms.services.setup import unmet_prerequisites


class Command(BaseCommand):
    help = "Report the same unmet LMS prerequisites used by module registration."

    def handle(self, **options):
        missing = unmet_prerequisites()
        if missing:
            raise CommandError("\n".join(missing))
        self.stdout.write(self.style.SUCCESS("LMS prerequisites satisfied."))
