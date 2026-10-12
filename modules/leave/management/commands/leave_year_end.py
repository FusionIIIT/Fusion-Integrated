"""Run the leave-year boundary from the shell (the beat timer calls the
same service; this is the manual/audited path).

    manage.py leave_year_end [--year 2026]
"""
from django.core.management.base import BaseCommand, CommandError

from modules.leave.services import policy as policy_service
from modules.leave.services import yearend


class Command(BaseCommand):
    help = "Lapse, convert and carry leave balances across a year boundary."

    def add_arguments(self, parser):
        parser.add_argument("--year", type=int, default=None,
                            help="Leave year to close (default: last year).")

    def handle(self, *args, **options):
        year = options["year"]
        if year is None:
            year = policy_service.current_leave_year() - 1
        try:
            result = yearend.run_year_end(year)
        except Exception as exc:  # ConflictError for an already-run year
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(
            f"leave year {year}: {result}"))
