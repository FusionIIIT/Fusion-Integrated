from django.core.management.base import BaseCommand

from modules.visitors_hostel.services.alerts import generate_stay_alerts


class Command(BaseCommand):
    help = "Queue VHMS no-show and overstay alerts."

    def handle(self, *args, **options):
        count = generate_stay_alerts()
        self.stdout.write(self.style.SUCCESS(f"Queued {count} VHMS stay alerts."))
