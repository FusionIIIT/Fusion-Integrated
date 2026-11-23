from django.core.management.base import BaseCommand

from modules.lms.tasks import release_due_materials


class Command(BaseCommand):
    help = "Publish up to 50 due scheduled materials through the locked transition service."

    def handle(self, **options):
        self.stdout.write(f"Released {release_due_materials()} materials.")
