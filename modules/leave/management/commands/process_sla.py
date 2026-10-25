from django.core.management.base import BaseCommand
from django.utils import timezone

from modules.leave.models import LeaveRequest, LeaveSLAConfig


class Command(BaseCommand):
    help = "Process SLA reminders/escalations for pending leave requests (pending-only)."

    def handle(self, *args, **options):
        cfg = LeaveSLAConfig.objects.filter(is_active=True).first()
        reminder_days = cfg.reminder_days if cfg else 3
        escalation_days = cfg.escalation_days if cfg else 7
        now = timezone.now()
        pending = LeaveRequest.objects.filter(status="pending")
        reminded = escalated = 0
        for lr in pending:
            age = (now - lr.created_at).days
            if age >= escalation_days:
                self.stdout.write(
                    self.style.WARNING(f"ESCALATE leave #{lr.id} (age {age}d) -> higher authority")
                )
                escalated += 1
            elif age >= reminder_days:
                self.stdout.write(f"REMIND leave #{lr.id} (age {age}d) -> assignee")
                reminded += 1
        self.stdout.write(
            self.style.SUCCESS(f"SLA processed: {reminded} reminded, {escalated} escalated")
        )
