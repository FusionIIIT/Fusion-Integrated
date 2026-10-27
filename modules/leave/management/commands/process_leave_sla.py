from django.core.management.base import BaseCommand
from modules.leave.services import process_sla_reminders_and_escalations

class Command(BaseCommand):
    help = 'Process SLA reminders and escalations for leave requests'

    def handle(self, *args, **kwargs):
        results = process_sla_reminders_and_escalations()
        self.stdout.write(self.style.SUCCESS(f'SLA processing completed. Results: {results}'))