"""Run EL-UC-021 once.

    manage.py process_leave_sla

Reminders and escalations go to the notification outbox, so run
`send_notifications` (or the equivalent worker) afterwards to drain it.
"""
from django.core.management.base import BaseCommand

from modules.leave.services import sla


class Command(BaseCommand):
    help = "Process SLA reminder and escalation thresholds for pending leave tasks."

    def handle(self, *args, **options):
        report = sla.process()
        self.stdout.write(self.style.SUCCESS(
            f"reminded {report['reminded']}, escalated {report['escalated']}, "
            f"skipped {report['skipped']}"))
