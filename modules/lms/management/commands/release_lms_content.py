from django.core.management.base import BaseCommand

from modules.lms.services.courses import release_due


class Command(BaseCommand):
    help = "Release due scheduled LMS content."

    def handle(self, *args, **options):
        self.stdout.write(str(release_due()) + " items released")
