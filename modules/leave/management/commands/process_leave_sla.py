from django.core.management.base import BaseCommand
from modules.leave.services.sla import process_sla_thresholds


class Command(BaseCommand):
    help = "Issue reminders and escalations for still-pending leave workflow tasks."

    def handle(self, *args, **options):
        result = process_sla_thresholds()
        self.stdout.write(" ".join(f"{key}={value}" for key, value in result.items()))
