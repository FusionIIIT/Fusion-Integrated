# Manual operator trigger for PSM SLA reminder and escalation sweep (BR-PSM-014).
from django.core.management.base import BaseCommand

from modules.psm.services.approvals import sweep_slas


class Command(BaseCommand):
    help = "Run the PSM approval SLA reminder and escalation sweep once."

    def handle(self, *args, **options):
        result = sweep_slas()
        msg = f"SLA sweep complete: {result['reminded']} reminded, {result['escalated']} escalated."
        self.stdout.write(self.style.SUCCESS(msg))
