"""Run the leave year-end close from the command line, after a dry run.

The dry run is the point: it prints the same report without writing, so an
administrator sees what would be credited, lapsed and converted before any of it
becomes someone's balance.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from modules.leave.services import admin, year_end


class Command(BaseCommand):
    help = "Run the ELM year-end close (lapse, carry forward, convert)."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--year", type=int, required=True,
                            help="The year to close.")
        parser.add_argument("--user", type=int, action="append", dest="users",
                            help="Limit to one user id; repeatable.")
        parser.add_argument("--dry-run", action="store_true",
                            help="Report what would happen, and write nothing.")

    def handle(self, *args, **options) -> None:
        pol = admin.read_policy()
        today = timezone.now().date()
        if not year_end.is_due(today=today, policy=pol) and not options["dry_run"]:
            raise CommandError(
                f"The configured year-end month is {pol.year_end_month}, and today "
                f"is {today:%B}. Run with --dry-run to see the effect first.")

        report = year_end.run(year=options["year"], user_ids=options["users"],
                              dry_run=options["dry_run"])
        self.stdout.write(str(report))
        for problem in report.exceptions:
            self.stderr.write(f"  user {problem['user_id']}: {problem['error']}")
        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("Dry run: nothing was written."))