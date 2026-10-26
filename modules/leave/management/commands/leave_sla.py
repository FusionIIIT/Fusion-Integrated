from django.core.management.base import BaseCommand

from modules.leave.services import process_sla


class Command(BaseCommand):
    help = "Process pending ELM SLA reminder and escalation thresholds."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(f"Created {process_sla()} SLA event(s)."))
