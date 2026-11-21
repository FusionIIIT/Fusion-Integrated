"""Manual run of FTS scheduled draft cleanup task."""
from django.core.management.base import BaseCommand

from modules.fts.tasks import cleanup_discarded_drafts


class Command(BaseCommand):
    help = "Run the scheduled draft cleanup task manually."

    def handle(self, *args, **options):
        result = cleanup_discarded_drafts()
        self.stdout.write(self.style.SUCCESS(f"Draft cleanup executed: {result}"))
