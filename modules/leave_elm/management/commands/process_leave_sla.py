from django.core.management.base import BaseCommand

from modules.leave_elm.services import process_sla_thresholds


class Command(BaseCommand):
    help = "Process pending ELM reminder and escalation thresholds."

    def handle(self, *args, **options):
        result = process_sla_thresholds()
        self.stdout.write(
            f"reminders={result['reminders']} escalations={result['escalations']}",
        )
