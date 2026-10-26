"""Year-end leave processing command (EL-UC-020, BR-EL-007, BR-EL-008).

Lapses unused CL/RH/SCL, converts faculty VL to EL at 2:1, and carries forward EL/COL.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from modules.elm.services import process_year_end


class Command(BaseCommand):
    help = "Execute event-triggered year-end leave balance conversion and carry-forward."

    def add_arguments(self, parser):
        parser.add_argument(
            "--year",
            type=int,
            default=timezone.localdate().year,
            help="Year to process (defaults to current calendar year).",
        )

    def handle(self, *args, **options):
        year = options["year"]
        result = process_year_end(year=year)
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully completed year-end processing for year {year}. "
                f"Users processed: {result['users_processed']}"
            )
        )
