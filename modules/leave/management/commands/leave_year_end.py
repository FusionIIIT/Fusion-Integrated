"""SF-EL-001. Close a leave year across everyone who holds a leave account.

A management command as well as a scheduled job, because the year-end run is
the one piece of this module that people will want to rehearse on a copy of
the data before letting it touch the real thing. `--dry-run` exists for exactly
that, and `--user` narrows it to one employee when a single account has to be
re-run after a correction.

The per-employee close is idempotent: an account already settled for the year
is skipped rather than settled twice.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.api.exceptions import ConflictError
from modules.directory.contracts import get_users
from modules.leave.models import LedgerEntry
from modules.leave.selectors.policy import NoEffectivePolicy
from modules.leave.services import yearend


class Command(BaseCommand):
    help = "Run the year-end lapse, carry-forward and VL-to-EL conversion."

    def add_arguments(self, parser):
        parser.add_argument("year", type=int, help="The year being closed.")
        parser.add_argument("--user", type=int, action="append", dest="users",
                            help="Close one employee only. Repeatable.")
        parser.add_argument("--credit-next", action="store_true",
                            help="Also credit the following year's entitlement.")
        parser.add_argument("--dry-run", action="store_true",
                            help="Report what would move and write nothing.")

    def handle(self, *args, **opts) -> None:
        year, dry = opts["year"], opts["dry_run"]
        people = opts["users"] or self._accounts(year)
        if not people:
            raise CommandError(f"No leave accounts carry entries for {year}.")

        faculty = self._faculty(people)
        closed = skipped = failed = 0
        totals = {"lapsed": 0, "carried": 0, "converted_vl": 0}

        for user_id in people:
            try:
                with transaction.atomic():
                    moved = yearend.close(
                        user_id=user_id, year=year, faculty=faculty.get(user_id, False))
                    if opts["credit_next"]:
                        yearend.credit_year(
                            user_id=user_id, year=year + 1,
                            faculty=faculty.get(user_id, False))
                    if dry:
                        transaction.set_rollback(True)
                closed += 1
                for k in totals:
                    totals[k] += moved[k]
            except ConflictError:
                skipped += 1
            except NoEffectivePolicy as exc:
                failed += 1
                self.stderr.write(self.style.ERROR(f"  {user_id}: {exc}"))

        self.stdout.write(
            f"  closed      {closed}\n"
            f"  skipped     {skipped}   (already closed)\n"
            f"  failed      {failed}\n"
            f"  lapsed      {totals['lapsed']}\n"
            f"  carried     {totals['carried']}\n"
            f"  VL converted {totals['converted_vl']}\n"
        )
        if dry:
            self.stdout.write(self.style.WARNING("  dry run — nothing was written"))
        elif failed:
            self.stdout.write(self.style.ERROR("  finished with errors"))
        elif not closed:
            self.stdout.write(self.style.WARNING(f"  {year} was already closed"))
        else:
            self.stdout.write(self.style.SUCCESS(f"  {year} closed"))

    def _accounts(self, year: int) -> list[int]:
        # order_by() clears the model's Meta.ordering, which Django would
        # otherwise add to the SELECT and defeat the DISTINCT, enumerating an
        # employee once per ledger row.
        return sorted(
            LedgerEntry.objects.filter(year=year).order_by()
            .values_list("user_id", flat=True).distinct()
        )

    def _faculty(self, user_ids: list[int]) -> dict[int, bool]:
        """One batched directory call. Faculty carry VL and convert it; nobody
        else does, so getting this wrong changes what people are owed."""
        return {
            uid: dto.kind == "faculty" for uid, dto in get_users(user_ids).items()
        }
