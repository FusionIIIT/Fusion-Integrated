"""Run one SLA reminder/escalation pass by hand (SF-EL-002)."""
from django.core.management.base import BaseCommand

from modules.elm.services import sla


class Command(BaseCommand):
    help = "Send due SLA reminders and escalations for pending ELM tasks"

    def handle(self, *args, **opts):
        self.stdout.write(str(sla.process()))
