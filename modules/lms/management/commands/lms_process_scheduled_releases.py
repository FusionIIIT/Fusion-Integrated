from django.core.management.base import BaseCommand
from modules.lms.services.release import process_due_scheduled_releases


class Command(BaseCommand):
    help = "Process due scheduled releases for course materials and assignments"

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=50,
            help="Maximum number of scheduled items to process in one batch",
        )

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        count = process_due_scheduled_releases(batch_size=batch_size)
        self.stdout.write(
            self.style.SUCCESS(f"Successfully processed {count} scheduled release(s).")
        )
