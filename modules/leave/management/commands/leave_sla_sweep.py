"""Run one SLA sweep from the shell, for hosts where the beat timer is not
the delivery mechanism (see schedule.py for what the timer runs)."""
from django.core.management.base import BaseCommand

from modules.leave.services import sla


class Command(BaseCommand):
    help = "Remind and escalate overdue leave tasks once."

    def handle(self, *args, **options):
        result = sla.sweep()
        self.stdout.write(self.style.SUCCESS(
            f"reminded {result['reminded']}, escalated {result['escalated']}"))
