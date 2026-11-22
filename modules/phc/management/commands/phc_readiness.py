from django.core.management.base import BaseCommand, CommandError

from modules.phc.registry import readiness


class Command(BaseCommand):
    help = "Report PHC prerequisites needed before the module can be enabled."

    def handle(self, *args, **options):
        missing = readiness()
        if missing:
            for item in missing:
                self.stdout.write(self.style.ERROR(item))
            raise CommandError("PHC is not ready.")
        self.stdout.write(self.style.SUCCESS("PHC is ready."))
