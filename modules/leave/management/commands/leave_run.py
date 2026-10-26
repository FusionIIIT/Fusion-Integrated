"""Run one of Leave's scheduled jobs by hand: notifications, sla, year-end or credit."""
from django.core.management.base import BaseCommand, CommandError

JOBS = ("notifications", "sla", "year-end", "credit")


class Command(BaseCommand):
    help = "Run a Leave scheduled job once, now"

    def add_arguments(self, parser):
        parser.add_argument("job", choices=JOBS)
        parser.add_argument("--year", type=int, help="The year for year-end or credit.")

    def handle(self, *args, **opts):
        from django.utils import timezone

        from modules.leave.services import notifications, sla, yearend

        job, year = opts["job"], opts.get("year")
        if job == "notifications":
            self.stdout.write(str(notifications.deliver_pending()))
        elif job == "sla":
            self.stdout.write(str(sla.process()))
        elif job == "year-end":
            if year is None:
                raise CommandError("Name the year to close: --year 2025")
            run = yearend.run(year)
            self.stdout.write(f"{run.year}: {run.status}, {run.accounts_processed} account(s), "
                              f"{run.entries_written} entr(ies)")
            for e in run.exceptions:
                self.stdout.write(self.style.WARNING(f"  user {e['user_id']}: {e['reason']}"))
        else:
            self.stdout.write(f"credited {yearend.credit_year(year or timezone.localdate().year)}")
