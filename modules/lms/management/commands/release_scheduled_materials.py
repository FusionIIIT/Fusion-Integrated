"""Management command to release scheduled course materials."""
from django.core.management.base import BaseCommand

from modules.lms.services.materials import release_scheduled_materials


class Command(BaseCommand):
    help = "Release scheduled LMS materials whose release time has arrived."

    def handle(self, *args, **options):
        count = release_scheduled_materials()
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully processed scheduled material release: {count} material(s) published."
            )
        )
