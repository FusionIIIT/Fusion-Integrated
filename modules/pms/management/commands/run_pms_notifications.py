"""Run the scheduled PMS notification drain synchronously."""

from django.core.management.base import BaseCommand, CommandError

from modules.pms.tasks import deliver_notifications


class Command(BaseCommand):
    help = "Drain pending PMS notifications without a Celery worker."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit", type=int, default=50, help="Maximum notifications to process."
        )

    def handle(self, *args, **options):
        if options["limit"] < 1:
            raise CommandError("The notification limit must be a positive integer.")
        sent = deliver_notifications.run(limit=options["limit"])
        self.stdout.write(f"sent={sent}")
