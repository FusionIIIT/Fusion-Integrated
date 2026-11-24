"""Management command to execute ELM year-end processing (EL-UC-020, CFR-EL-028)."""

from django.core.management.base import BaseCommand
from django.utils import timezone

from modules.elm.services.leave import execute_year_end_processing


class Command(BaseCommand):
    help = "Execute ELM year-end lapse, conversion, and carry-forward processing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--year",
            type=int,
            default=timezone.localdate().year,
            help="Year to process (defaults to current year)",
        )

    def handle(self, *args, **options):
        year = options["year"]
        self.stdout.write(f"Executing ELM year-end processing for year {year}...")
        summary = execute_year_end_processing(year)
        self.stdout.write(
            self.style.SUCCESS(
                f"Year-end {year} complete: {summary['lapsed_records']} lapsed, "
                f"{summary['vl_converted_faculty']} faculty VL converted, "
                f"{summary['carried_forward']} carried forward."
            )
        )
