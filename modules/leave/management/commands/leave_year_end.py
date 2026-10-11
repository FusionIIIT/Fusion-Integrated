"""Run EL-UC-020 for a leave year.

    manage.py leave_year_end --leave-year 2026

The event-triggered task calls the same service, so an operator running this by
hand and the boundary firing on its own cannot diverge.
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.api.exceptions import ConflictError
from modules.leave.services import year_end


class Command(BaseCommand):
    help = "Execute year-end leave processing for a leave year."

    def add_arguments(self, parser):
        parser.add_argument("--leave-year", type=int,
                            help="Leave year to close (default: previous year).")

    def handle(self, *args, **options):
        leave_year = options["leave_year"] or timezone.localdate().year - 1
        try:
            run = year_end.run(leave_year=leave_year)
        except ConflictError as exc:
            raise CommandError(f"{exc.code}: {exc.message}") from exc

        for exception in run.exceptions.all()[:20]:
            self.stderr.write(f"  exception: {exception}")
        self.stdout.write(self.style.SUCCESS(
            f"year-end {run.leave_year}: {run.status}, "
            f"{run.accounts_processed} account(s) processed, "
            f"{run.exceptions.count()} exception(s)"))
