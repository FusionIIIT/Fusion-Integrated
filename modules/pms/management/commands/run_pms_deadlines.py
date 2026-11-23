"""Run the scheduled PMS deadline monitor synchronously."""

from django.core.management.base import BaseCommand

from modules.pms.tasks import monitor_deadlines


class Command(BaseCommand):
    help = "Run one PMS deadline-monitor pass without a Celery worker."

    def handle(self, *args, **options):
        report = monitor_deadlines.run()
        self.stdout.write(
            " ".join(f"{key}={value}" for key, value in sorted(report.items()))
        )
