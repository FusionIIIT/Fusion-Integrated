import datetime

from django.core.management.base import BaseCommand

from modules.leave.services.yearend import run_year_end_processing


class Command(BaseCommand):
    help = (
        "Run year-end leave balance processing: lapse CL/RH/SCL, "
        "convert unavailed VL to EL, and carry forward balances."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--year", type=int, default=datetime.date.today().year, help="Year to process."
        )

    def handle(self, *args, **options):
        year = options["year"]
        self.stdout.write(f"Executing year-end processing for year {year}...")
        summary = run_year_end_processing(year=year)
        msg = (
            f"Year-end processing complete. Processed {summary['users_processed']} users, "
            f"created {summary['entries_created']} entries."
        )
        self.stdout.write(self.style.SUCCESS(msg))
