from django.core.management.base import BaseCommand

from modules.badms.tasks import check_backup_failure_sla


class Command(BaseCommand):
    help = "Enforce the 5-minute backup failure alerting SLA and trigger escalations."

    def handle(self, *args, **options):
        result = check_backup_failure_sla()
        self.stdout.write(
            self.style.SUCCESS(f"Dispatched {result.get('alerted', 0)} backup failure alerts.")
        )
