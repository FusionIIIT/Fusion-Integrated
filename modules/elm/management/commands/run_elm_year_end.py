"""Run year-end leave processing once by hand (SF-EL-001)."""
from django.core.management.base import BaseCommand
from django.utils import timezone

from modules.elm.services import year_end


class Command(BaseCommand):
    help = "Lapse, convert and carry forward leave balances for a closing year"

    def add_arguments(self, parser):
        parser.add_argument("--year", type=int, default=None,
                            help="the year being closed; defaults to last year")

    def handle(self, *args, **opts):
        year = opts["year"] or timezone.localdate().year - 1
        run = year_end.run(year)
        self.stdout.write(f"year {run.year}: {run.employees} employee(s), "
                          f"{len(run.exceptions)} exception(s)")
        for e in run.exceptions:
            self.stdout.write(self.style.WARNING(f"  {e}"))
