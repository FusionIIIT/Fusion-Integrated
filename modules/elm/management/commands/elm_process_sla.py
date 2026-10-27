"""Management command to process SLA reminders and escalations for pending leave requests."""
from django.core.management.base import BaseCommand

from modules.elm.services.admin import process_sla_sweep


class Command(BaseCommand):
    help = "Process pending leave requests for SLA reminders and escalations."

    def handle(self, *args, **options):
        result = process_sla_sweep()
        self.stdout.write(
            self.style.SUCCESS(
                f"SLA Sweep completed: {result['pending_checked']} checked, "
                f"{result['reminded']} reminded, {result['escalated']} escalated."
            )
        )
