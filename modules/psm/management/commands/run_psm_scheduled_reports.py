# Manual operator trigger for due PSM scheduled reports (PSM-UC-035).
from django.core.management.base import BaseCommand

from modules.psm.services.reports import run_due_schedules


class Command(BaseCommand):
    help = "Execute all due active PSM scheduled reports once."

    def handle(self, *args, **options):
        count = run_due_schedules()
        self.stdout.write(self.style.SUCCESS(f"Scheduled reports executed: {count}."))
