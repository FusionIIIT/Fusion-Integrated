from django.core.management.base import BaseCommand

from modules.leave.services.sla import process_sla_clocks


class Command(BaseCommand):
    help = "Process active leave SLA clocks, trigger reminders and auto-escalations."

    def handle(self, *args, **options):
        self.stdout.write("Processing leave SLA clocks...")
        res = process_sla_clocks()
        self.stdout.write(
            self.style.SUCCESS(
                f"Processed SLA clocks: {res['reminded']} reminded, {res['escalated']} escalated."
            )
        )
