from django.core.management.base import BaseCommand

from modules.cms.services import process_sla


class Command(BaseCommand):
    help = "Process configured CMS SLA reminders and escalation triggers."

    def handle(self, *args, **options):
        result = process_sla()
        self.stdout.write(
            self.style.SUCCESS(
                f"CMS SLA processing complete: {result['reminded']} reminder(s), "
                f"{result['escalated']} escalation(s)."
            )
        )
