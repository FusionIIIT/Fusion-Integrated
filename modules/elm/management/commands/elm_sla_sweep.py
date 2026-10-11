"""Run the SLA reminder/escalation pass (EL-UC-021) by hand."""
from django.core.management.base import BaseCommand

from modules.elm.services import scheduled


class Command(BaseCommand):
    help = "Remind and escalate still-pending leave tasks"

    def handle(self, *args, **opts):
        self.stdout.write(str(scheduled.sla_sweep()))
