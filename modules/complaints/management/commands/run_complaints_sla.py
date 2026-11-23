"""Management command to process Complaint SLA lifecycle events.

Enforces:
- BR-CMS-028 / UC-CMS-021: Pre-breach SLA reminders.
- BR-CMS-029 / UC-CMS-022 / BW-CMS-08: Automatic SLA breach escalation.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from modules.complaints.models import Complaint, ComplaintStatus
from modules.complaints.services import complaints as complaint_services


class Command(BaseCommand):
    help = (
        "Process Complaint Management System SLA lifecycle events: "
        "pre-breach reminders (BR-CMS-028) and automatic breach escalation (BR-CMS-029)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--check-only",
            action="store_true",
            help="Report current SLA status and pending actions without mutating database.",
        )
        parser.add_argument(
            "--escalate-only",
            action="store_true",
            help="Run only automatic SLA breach escalation (BR-CMS-029).",
        )
        parser.add_argument(
            "--remind-only",
            action="store_true",
            help="Run only pre-breach SLA reminder dispatch (BR-CMS-028).",
        )

    def handle(self, *args, **options) -> None:
        now = timezone.now()
        check_only = options.get("check_only", False)
        escalate_only = options.get("escalate_only", False)
        remind_only = options.get("remind_only", False)

        unresolved = [ComplaintStatus.SUBMITTED.value, ComplaintStatus.IN_PROGRESS.value]

        if check_only:
            overdue_count = Complaint.objects.filter(
                status__in=unresolved,
                is_escalated=False,
                sla_deadline__isnull=False,
                sla_deadline__lt=now,
            ).count()

            pending_reminders = Complaint.objects.filter(
                status__in=unresolved,
                is_escalated=False,
                sla_reminder_sent=False,
                sla_deadline__isnull=False,
                sla_deadline__gt=now,
            )
            reminder_candidates = 0
            for c in pending_reminders:
                total = (c.sla_deadline - c.created_at).total_seconds()
                elapsed = (now - c.created_at).total_seconds()
                if total > 0 and (elapsed / total) >= 0.75:
                    reminder_candidates += 1

            self.stdout.write("CMS SLA Status Report:")
            self.stdout.write(f"  Overdue complaints awaiting escalation: {overdue_count}")
            self.stdout.write(f"  Complaints eligible for pre-breach reminder (>=75% elapsed): {reminder_candidates}")
            return

        escalated = 0
        reminded = 0

        if not remind_only:
            escalated = complaint_services.check_and_escalate_sla_breaches()
            if escalated:
                self.stdout.write(self.style.SUCCESS(f"Successfully auto-escalated {escalated} breached complaint(s)."))
            else:
                self.stdout.write("No overdue complaints required escalation.")

        if not escalate_only:
            reminded = complaint_services.check_and_send_sla_reminders()
            if reminded:
                self.stdout.write(self.style.SUCCESS(f"Successfully dispatched {reminded} pre-breach reminder(s)."))
            else:
                self.stdout.write("No complaints currently eligible for pre-breach reminder.")

        self.stdout.write(self.style.SUCCESS(f"SLA run completed. (Escalated: {escalated}, Reminders: {reminded})"))
