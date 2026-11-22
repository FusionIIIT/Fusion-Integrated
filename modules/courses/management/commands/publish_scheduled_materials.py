"""Management command to release scheduled course materials whose release time has passed."""
from django.core.management.base import BaseCommand

from modules.courses.services.materials import publish_scheduled_materials


class Command(BaseCommand):
    help = "Publish course materials whose scheduled release_at timestamp has passed."

    def handle(self, *args, **options):
        count = publish_scheduled_materials()
        self.stdout.write(
            self.style.SUCCESS(f"Successfully processed scheduled materials: {count} released.")
        )

