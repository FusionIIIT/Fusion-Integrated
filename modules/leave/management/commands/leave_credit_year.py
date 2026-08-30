"""Credit a year's entitlement to every employee.

The counterpart to leave_year_end. A policy that grants 8 casual leave grants
nobody anything until this has run: the balance is a sum of ledger rows, and
without a credit row the sum is zero and every application is refused for
insufficient balance.

Run it once when a year opens. It is idempotent per employee and category, so
running it again after new staff join credits only the people who were missed.
"""
from django.core.management.base import BaseCommand, CommandError

from modules.directory.contracts import (
    employees_missing_from_projection,
    get_employees,
)
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
        parser.add_argument(
            "--accept-incomplete", action="store_true",
            help="Credit everyone the directory holds even though it is short of "
                 "what the identity service reports. Use when the shortfall is "
                 "known and being fixed elsewhere.")

    def _everyone(self, *, accept_incomplete: bool) -> list:
        """Every employee, or nothing.

        The directory is a projection that fills in as people are looked up, so
        it is routinely a fraction of the institute. Crediting whoever happens
        to be cached would report success and quietly leave most of the staff
        with no entitlement -- which surfaces months later as one person unable
        to apply, not as a failed command.
        """
        employees = get_employees()
        if not employees:
            raise CommandError(
                "The directory holds no employees. Run sync_identity on the IAM, "
                "then populate this service's projection, before crediting.")
        missing = employees_missing_from_projection()
        if missing == []:
            return employees
        if missing is None:
            described = "the identity service is unreachable, so completeness is unknown"
        else:
            described = (
                f"{len(missing)} employee(s) the identity service knows are not in "
                f"this directory: {missing[:10]}"
                + (" ..." if len(missing) > 10 else "")
            )
        if not accept_incomplete:
            raise CommandError(
                f"{described}. Crediting now would leave them with no entitlement "
                "at all. Run sync_directory, then this again. If the shortfall is "
                "known and being fixed elsewhere, re-run with --accept-incomplete.")
        self.stdout.write(self.style.WARNING(f"  proceeding anyway: {described}"))
        return employees

    def handle(self, *args, **opts) -> None:
        year, dry = opts["year"], opts["dry_run"]
        if opts["users"]:
            wanted = set(opts["users"])
            employees = [e for e in get_employees() if e.user_id in wanted]
            missing = wanted - {e.user_id for e in employees}
            if missing:
                raise CommandError(
                    f"Not in the directory: {sorted(missing)}. They are either not "
                    "employees or have never been seen by this service.")
        else:
            employees = self._everyone(accept_incomplete=opts["accept_incomplete"])

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
