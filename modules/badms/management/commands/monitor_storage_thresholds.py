from django.core.management.base import BaseCommand

from modules.badms.tasks import monitor_storage_thresholds


class Command(BaseCommand):
    help = "Evaluate user storage quotas and update threshold exhaustion flags."

    def handle(self, *args, **options):
        result = monitor_storage_thresholds()
        self.stdout.write(
            self.style.SUCCESS(f"Updated {result.get('updated', 0)} storage quota thresholds.")
        )
