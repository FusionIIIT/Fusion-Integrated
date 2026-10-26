"""Run the SLA reminder and escalation sweep by hand (WF-EL-08)."""
from django.core.management.base import BaseCommand

from modules.elm.services import sla


class Command(BaseCommand):
    help = "Remind and escalate leave tasks that have waited too long"

    def handle(self, *args, **opts):
        report = sla.run()
        self.stdout.write(f"reminded {report.reminded}, escalated {report.escalated}")
