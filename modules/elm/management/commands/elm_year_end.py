from datetime import date

from django.core.management.base import BaseCommand, CommandError

from modules.elm.services import policy, scheduled


class Command(BaseCommand):
    help = "Year-end leave processing (SF-EL-001): lapse, VL-to-EL conversion, carry-forward."

    def add_arguments(self, parser):
        parser.add_argument("--year", type=int, default=date.today().year)
        parser.add_argument("--no-credit", action="store_true",
                            help="Skip crediting next year's entitlements.")

    def handle(self, *args, **opts):
        year = opts["year"]
        try:
            summary = scheduled.process_year_end(year)
        except policy.NoPublishedPolicy as exc:
            raise CommandError(f"Year-end processing failed: {exc}") from exc

        self.stdout.write(f"Year-end {year}: {summary['lapsed']} lapsed, "
                          f"{summary['converted']} VL converted, {summary['carried']} carried.")
        for exc in summary["exceptions"]:
            self.stderr.write(f"EXCEPTION user {exc['user_id']}: {exc['error']}")
        if not opts["no_credit"]:
            try:
                n = scheduled.credit_year(year + 1)
            except policy.NoPublishedPolicy as exc:
                raise CommandError(f"Year credit failed: {exc}") from exc
            self.stdout.write(f"Credited {n} entitlement(s) for {year + 1}.")
