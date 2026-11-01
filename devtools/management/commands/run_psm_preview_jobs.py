import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from modules.psm.tasks import monitor_sla, run_reports


class Command(BaseCommand):
    help = "Run PSM timers for the isolated preview; production uses Celery beat."

    def handle(self, *args, **options):
        if not getattr(settings, "PSM_PREVIEW", False):
            raise CommandError("This command is for the isolated PSM preview only.")
        while True:
            monitor_sla()
            run_reports()
            time.sleep(30)
