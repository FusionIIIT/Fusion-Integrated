"""Execute year-end leave balance processing CLI command (EL-UC-020 / CFR-EL-028)."""
from django.core.management.base import BaseCommand
from django.utils import timezone

from modules.elm.services.year_end import execute_year_end_processing


class Command(BaseCommand):
    help = (
        "Run ELM annual year-end leave processing (lapse CL/RH/SCL, convert faculty VL to EL, "
        "carry-forward EL/COL)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--academic-year",
            type=str,
            default="",
            help="Academic year label, e.g. '2024-25'. Defaults to current year.",
        )
        parser.add_argument(
            "--run-by",
            type=int,
            default=1,
            help="ID of the user running this year-end process (default: 1).",
        )

    def handle(self, *args, **options):
        academic_year = options["academic_year"].strip()
        if not academic_year:
            now = timezone.now()
            academic_year = f"{now.year}-{str(now.year + 1)[-2:]}"

        run_by = options["run_by"]
        self.stdout.write(
            f"Starting ELM year-end processing for {academic_year} (run_by: {run_by})..."
        )

        year_end_run = execute_year_end_processing(
            academic_year=academic_year,
            run_by_user_id=run_by,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully completed year-end processing for {academic_year}. "
                f"Processed {year_end_run.accounts_processed_count} accounts. "
                f"Run ID: {year_end_run.pk}"
            )
        )
