from django.core.management.base import BaseCommand
from django.utils import timezone

from modules.oap.models import ReminderPolicy


class Command(BaseCommand):
    help = "Add a reminder policy. Policies are never edited: a new row supersedes the old."

    def add_arguments(self, parser):
        parser.add_argument("--after-hours", type=int, required=True)
        parser.add_argument("--by", type=int, required=True, dest="by_user_id")

    def handle(self, *args, **options):
        hours = options["after_hours"]
        if hours < 1:
            self.stderr.write("after-hours must be at least 1.")
            return
        row = ReminderPolicy.objects.create(
            effective_from=timezone.now(),
            after_hours=hours,
            created_by_user_id=options["by_user_id"],
        )
        self.stdout.write(self.style.SUCCESS(f"Reminder policy {row.pk}: after {hours} hours."))
