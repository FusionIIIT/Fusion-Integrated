"""Run the year-end job by hand (WF-EL-07).

    manage.py elm_year_end 2026
"""
from django.core.management.base import BaseCommand

from modules.elm.services import year_end


class Command(BaseCommand):
    help = "Lapse, convert and carry forward leave balances for a finished year"

    def add_arguments(self, parser):
        parser.add_argument("year", type=int)
        parser.add_argument("--force", action="store_true",
                            help="Allow a year that has not finished (testing only).")

    def handle(self, *args, **opts):
        report = year_end.run(opts["year"], force=opts["force"])
        self.stdout.write(
            f"year {report.year}: {report.processed} balance(s) closed, "
            f"{report.lapsed_days} lapsed, {report.carried_days} carried, "
            f"{report.converted_el_days} EL from VL, "
            f"{len(report.skipped_user_ids)} user(s) skipped")
