"""Process SLA thresholds and escalation events CLI command (EL-UC-021)."""
from django.core.management.base import BaseCommand
from django.utils import timezone

from modules.elm.services.sla import process_sla_events


class Command(BaseCommand):
    help = "Evaluate active ELM workflow tasks against SLA thresholds and mark overdue/escalated."

    def handle(self, *args, **options):
        now = timezone.now()
        self.stdout.write(f"Evaluating ELM workflow task SLA states at {now.isoformat()}...")

        processed_count = process_sla_events(now=now)

        self.stdout.write(
            self.style.SUCCESS(
                f"SLA processing complete. {processed_count} tasks evaluated / transitioned."
            )
        )
