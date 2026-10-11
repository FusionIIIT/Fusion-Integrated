"""Run year-end leave processing (EL-UC-020) by hand."""
from django.core.management.base import BaseCommand

from modules.elm.services import scheduled


class Command(BaseCommand):
    help = "Lapse, convert and carry forward leave for a finished year"

    def add_arguments(self, parser):
        parser.add_argument("--year", type=int, default=None,
                            help="The year that ended (default: last year).")

    def handle(self, *args, **opts):
        report = scheduled.year_end(opts["year"] or scheduled.previous_year())
        self.stdout.write(str(report))
