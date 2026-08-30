"""Credit a year's entitlement to every employee.

The counterpart to leave_year_end. A policy that grants 8 casual leave grants
nobody anything until this has run: the balance is a sum of ledger rows, and
without a credit row the sum is zero and every application is refused for
insufficient balance.

Run it once when a year opens. It is idempotent per employee and category, so
running it again after new staff join credits only the people who were missed.
"""
from django.core.management.base import BaseCommand, CommandError

from modules.directory.contracts import get_employees
from modules.leave.selectors.policy import NoEffectivePolicy
from modules.leave.services import yearend


class Command(BaseCommand):
    help = "Credit the annual leave entitlement for a year."

    def add_arguments(self, parser):
        parser.add_argument("year", type=int)
        parser.add_argument("--user", type=int, action="append", dest="users",
                            help="Credit one employee only. Repeatable.")
        parser.add_argument("--dry-run", action="store_true",
                            help="Report who would be credited and write nothing.")

    def handle(self, *args, **opts) -> None:
        year, dry = opts["year"], opts["dry_run"]
        employees = get_employees()
        if opts["users"]:
            wanted = set(opts["users"])
            employees = [e for e in employees if e.user_id in wanted]
        if not employees:
            raise CommandError(
                "No employees found. The directory is empty — run sync_identity "
                "on the IAM first.")

        credited = untouched = 0
        rows = 0
        for employee in employees:
            try:
                if dry:
                    credited += 1
                    continue
                written = yearend.credit_year(
                    user_id=employee.user_id, year=year,
                    faculty=employee.kind == "faculty")
            except NoEffectivePolicy as exc:
                raise CommandError(str(exc)) from exc
            if written:
                credited += 1
                rows += written
            else:
                untouched += 1

        self.stdout.write(
            f"  employees   {len(employees)}\n"
            f"  credited    {credited}\n"
            f"  already had {untouched}\n"
            f"  entries     {rows}\n")
        if dry:
            self.stdout.write(self.style.WARNING("  dry run — nothing was written"))
        else:
            self.stdout.write(self.style.SUCCESS(f"  {year} entitlement credited"))
