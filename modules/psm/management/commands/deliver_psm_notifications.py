# Manual operator trigger for delivering queued PSM notifications (BR-PSM-006).
from django.core.management.base import BaseCommand

from modules.psm.services.common import deliver_pending_notifications


class Command(BaseCommand):
    help = "Deliver queued PSM lifecycle notifications once."

    def handle(self, *args, **options):
        count = deliver_pending_notifications()
        self.stdout.write(self.style.SUCCESS(f"Delivered {count} PSM notification(s)."))
