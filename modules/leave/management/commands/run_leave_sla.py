"""Send SLA reminders and escalations by hand.

Useful when a threshold is changed mid-day and the next beat is too far away to
trust in a test or an incident.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from modules.leave.services import sla


class Command(BaseCommand):
    help = "Fire due ELM SLA reminders and escalations now."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--reminders-only", action="store_true")
        parser.add_argument("--escalations-only", action="store_true")

    def handle(self, *args, **options) -> None:
        if not options["escalations_only"]:
            self.stdout.write(f"reminders sent: {sla.remind()}")
        if not options["reminders_only"]:
            self.stdout.write(f"escalations: {sla.escalate()}")