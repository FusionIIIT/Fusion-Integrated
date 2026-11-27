"""Execute year-end leave balance processing (BR-EL-002..009, EL-UC-020).

Lapses unused CL, RH, SCL; converts unused faculty VL to EL at 2:1 ratio;
carries forward EL and COL according to policy and configured ceilings.
Idempotent per employee and leave year.
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from modules.leave.services.year_end import process_year_end


class Command(BaseCommand):
    help = "Execute year-end leave entitlement processing (lapses, conversions, carry forwards)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--year",
            type=int,
            default=None,
            help="The leave year to close. Defaults to current_year - 1.",
        )
        parser.add_argument(
            "--to-year",
            type=int,
            default=None,
            help="The target leave year to receive carried balances. Defaults to year + 1.",
        )
        parser.add_argument(
            "--user-id",
            type=int,
            default=None,
            help="Target a specific employee by ID rather than all employees.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Rehearse the run inside a rolled-back transaction without saving changes.",
        )
        parser.add_argument(
            "--el-ceiling",
            type=Decimal,
            default=None,
            help="Optional ceiling for EL carry-forward (e.g. 300.0).",
        )
        parser.add_argument(
            "--col-ceiling",
            type=Decimal,
            default=None,
            help="Optional ceiling for COL carry-forward.",
        )

    def handle(self, *args, **options):
        from_year = options["year"]
        if from_year is None:
            from_year = timezone.now().year - 1

        to_year = options["to_year"] or (from_year + 1)
        dry_run = options["dry_run"]
        target_uid = options["user_id"]
        user_ids = [target_uid] if target_uid is not None else None

        ceilings = {}
        if options["el_ceiling"] is not None:
            ceilings["EL"] = options["el_ceiling"]
        if options["col_ceiling"] is not None:
            ceilings["COL"] = options["col_ceiling"]

        dry_label = " (DRY RUN)" if dry_run else ""
        self.stdout.write(
            f"Starting year-end leave processing for year {from_year} -> {to_year}{dry_label}"
        )

        report = process_year_end(
            from_year=from_year,
            to_year=to_year,
            user_ids=user_ids,
            ceilings=ceilings if ceilings else None,
            dry_run=dry_run,
        )

        self.stdout.write(f"  Processed employees: {report.processed_users}")
        self.stdout.write(f"  Skipped (already closed): {report.skipped_users}")
        self.stdout.write(f"  Total lapsed: {dict(report.total_lapsed)}")
        self.stdout.write(f"  Total converted: {dict(report.total_converted)}")
        self.stdout.write(f"  Total carried forward: {dict(report.total_carried_forward)}")

        if report.exceptions:
            self.stdout.write(self.style.WARNING(f"  Exceptions ({len(report.exceptions)}):"))
            for exc in report.exceptions[:10]:
                self.stdout.write(self.style.WARNING(f"    - {exc}"))

        if dry_run:
            self.stdout.write(self.style.NOTICE("  Dry run complete — all changes rolled back."))
        else:
            self.stdout.write(self.style.SUCCESS("  Year-end processing completed successfully."))
