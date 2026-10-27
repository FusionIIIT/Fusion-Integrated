"""Management command to process SLA reminders and escalations for pending leave requests.

Usage:
    python manage.py process_elm_sla
"""
from django.core.management.base import BaseCommand
from modules.elm.services.leave_service import process_sla_thresholds


class Command(BaseCommand):
    help = "Process SLA threshold reminders and escalations for pending ELM tasks (BR-EL-032, BR-EL-033)."

    def handle(self, *args, **options):
        self.stdout.write("Processing ELM SLA threshold checks...")
        res = process_sla_thresholds()
        self.stdout.write(
            self.style.SUCCESS(
                f"SLA Sweep Completed:\n"
                f"  - Total pending checked: {res['total_pending_checked']}\n"
                f"  - Reminders logged: {res['reminded_count']}\n"
                f"  - Escalations executed: {res['escalated_count']}"
            )
        )
