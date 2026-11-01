from django.core.management.base import BaseCommand

from modules.patents import services


class Command(BaseCommand):
    help = "Expire applications whose 60-day resubmission window has closed."

    def handle(self, *args, **options):
        count = services.sweep_expired()
        self.stdout.write(f"expired {count} application(s)")
