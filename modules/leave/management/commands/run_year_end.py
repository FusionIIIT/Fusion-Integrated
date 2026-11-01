"""Run the year-end pass by hand (EL-UC-020).

    manage.py run_year_end --year 2026
    manage.py run_year_end --year 2026 --dry-run
"""
from django.core.management.base import BaseCommand, CommandError

from modules.leave.domain import ledger as led
from modules.leave.models import LeaveAccount
from modules.leave.services import yearend


class Command(BaseCommand):
    help = "Lapse, carry forward and convert leave accounts at year end"

    def add_arguments(self, parser):
        parser.add_argument("--year", type=int,
                            help="The year to settle; defaults to every past year.")
        parser.add_argument("--dry-run", action="store_true",
                            help="Report what would be written, and write nothing.")

    def handle(self, *args, **opts):
        years = [opts["year"]] if opts["year"] else yearend.years_to_settle()
        if not years:
            self.stdout.write("  nothing to settle")
            return

        for year in years:
            if opts["dry_run"]:
                self._preview(year)
                continue
            report = yearend.run(year=year)
            self.stdout.write(
                f"  {year}: accounts={report['accounts']} "
                f"lapsed={report['lapsed']} carried={report['carried']} "
                f"converted_el={report['converted_el']} "
                f"exceptions={len(report['exceptions'])}")
            for problem in report["exceptions"]:
                self.stdout.write(self.style.ERROR(f"    account {problem['account']}: "
                                                   f"{problem['error']}"))

    def _preview(self, year: int) -> None:
        accounts = LeaveAccount.objects.filter(year=year)
        if not accounts.exists():
            raise CommandError(f"No leave account exists for {year}.")
        self.stdout.write(f"  {year}: {accounts.count()} account(s) would be settled")
        for account in accounts.order_by("user_id", "category")[:20]:
            closing = led.project(account.entries.values_list("entry_type", "days")
                                  .order_by("id"))
            self.stdout.write(f"    u{account.user_id} {account.category} "
                              f"closing={closing}")
