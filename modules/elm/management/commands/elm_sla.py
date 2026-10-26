from django.core.management.base import BaseCommand

from modules.elm.services import scheduled


class Command(BaseCommand):
    help = "SLA reminders and escalations for pending workflow tasks (SF-EL-002)."

    def handle(self, *args, **opts):
        s = scheduled.process_sla()
        self.stdout.write(f"SLA: {s['reminders']} reminder(s), {s['escalations']} escalation(s).")
