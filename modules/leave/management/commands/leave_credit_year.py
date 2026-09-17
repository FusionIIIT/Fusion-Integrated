"""Credit a year's entitlement to every employee."""
from django.core.management.base import BaseCommand, CommandError

from core.api.exceptions import ConflictError
from modules.directory.contracts import (
    employee_projection_disagreement,
    get_employees,
)
from modules.leave.models import EntryReason, LedgerEntry
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
            "--revoke", action="store_true",
            help="Reverse the credit for people this directory no longer calls "
                 "employees. Writes reversing entries; refuses where any of it "
                 "has been used.")
        parser.add_argument(
            "--accept-incomplete", action="store_true",
            help="Credit everyone the directory holds even though it is short of "
                 "what the identity service reports. Use when the shortfall is "
                 "known and being fixed elsewhere.")

    def _revoke(self, year: int, dry: bool) -> None:
        """Take back what was credited to people who are not employees."""
        entitled = {e.user_id for e in get_employees()}
        credited = set(
            LedgerEntry.objects.filter(year=year, reason=EntryReason.ANNUAL_CREDIT)
            .order_by().values_list("user_id", flat=True).distinct()
        )
        wrongly = sorted(credited - entitled)
        if not wrongly:
            self.stdout.write(self.style.SUCCESS(
                f"  every {year} credit belongs to a current employee"))
            return

        self.stdout.write(f"  credited but not employees: {len(wrongly)}")
        if dry:
            self.stdout.write(f"    {wrongly[:20]}")
            self.stdout.write(self.style.WARNING("  dry run — nothing was written"))
            return

        reversed_rows = refused = 0
        for user_id in wrongly:
            try:
                reversed_rows += yearend.revoke_credit(
                    user_id=user_id, year=year, actor_user_id=0,
                    note=f"not an employee at the {year} credit")
            except ConflictError as exc:
                refused += 1
                self.stderr.write(self.style.ERROR(f"    {user_id}: {exc.message}"))
        self.stdout.write(
            f"  reversed  {reversed_rows} entr(y/ies)\n"
            f"  refused   {refused}   (leave already used — settle by hand)\n")
        self.stdout.write(self.style.SUCCESS("  credits reversed"))

    def _everyone(self, *, accept_incomplete: bool) -> list:
        """Every employee, or nothing."""
        employees = get_employees()
        if not employees:
            raise CommandError(
                "The directory holds no employees. Run sync_identity on the IAM, "
                "then populate this service's projection, before crediting.")
        disagreement = employee_projection_disagreement()
        if disagreement is None:
            described = "the identity service is unreachable, so completeness is unknown"
        else:
            missing, stale = disagreement
            if not missing and not stale:
                return employees
            parts = []
            if missing:
                parts.append(
                    f"{len(missing)} the identity service knows and this directory "
                    f"does not: {missing[:10]}" + (" ..." if len(missing) > 10 else ""))
            if stale:
                # Crediting non-employees is the more expensive mistake.
                parts.append(
                    f"{len(stale)} this directory still calls employees and the "
                    f"identity service does not: {stale[:10]}"
                    + (" ..." if len(stale) > 10 else ""))
            described = "; ".join(parts)
        if not accept_incomplete:
            raise CommandError(
                f"{described}. Crediting now would leave them with no entitlement "
                "at all. Run sync_directory, then this again. If the shortfall is "
                "known and being fixed elsewhere, re-run with --accept-incomplete.")
        self.stdout.write(self.style.WARNING(f"  proceeding anyway: {described}"))
        return employees

    def handle(self, *args, **opts) -> None:
        year, dry = opts["year"], opts["dry_run"]
        if opts["revoke"]:
            self._revoke(year, dry)
            return
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
