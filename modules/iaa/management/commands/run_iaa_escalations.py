"""Manually run the overdue approval timeout escalation task."""

from django.core.management.base import BaseCommand

from modules.iaa.tasks import escalate_overdue_approvals


class Command(BaseCommand):
    help = "Run overdue approval escalation."

    def handle(self, *args, **options):
        count = escalate_overdue_approvals()
        self.stdout.write(
            self.style.SUCCESS(f"Successfully processed escalations. Items escalated: {count}")
        )
