"""Advance approved leave as the calendar has moved."""
from datetime import date

from django.core.management.base import BaseCommand

from modules.leave.services import scheduler


class Command(BaseCommand):
    help = "Start leave that has begun and close leave that has ended."

    def add_arguments(self, parser):
        parser.add_argument("--on", help="Act as though today were this date "
                                        "(YYYY-MM-DD). For catching up.")
        parser.add_argument("--status", action="store_true",
                            help="Report what is due and exit. Moves nothing.")

    def handle(self, *args, **opts) -> None:
        on = date.fromisoformat(opts["on"]) if opts["on"] else date.today()

        if opts["status"]:
            self._status(on)
            return

        report = scheduler.advance(on)
        self.stdout.write(
            f"  started   {report.started}   (leave whose first day has arrived)\n"
            f"  ended     {report.ended}   (leave awaiting a resumption report)\n"
            f"  failed    {report.failed}\n")
        if report.failed:
            self.stdout.write(self.style.ERROR("  see the log for what could not move"))
        elif report.moved:
            self.stdout.write(self.style.SUCCESS(f"  {report.moved} request(s) advanced"))
        else:
            self.stdout.write(self.style.SUCCESS("  nothing was due"))

    def _status(self, on: date) -> None:
        begin, end = scheduler.due_to_begin(on), scheduler.due_to_end(on)
        self.stdout.write(f"  as at {on}:")
        self.stdout.write(f"    due to begin  {len(begin)}")
        for r in begin[:10]:
            self.stdout.write(f"      request {r.pk:<6} user {r.user_id:<6} "
                              f"{r.category} from {r.starts_on}")
        self.stdout.write(f"    due to end    {len(end)}")
        for r in end[:10]:
            self.stdout.write(f"      request {r.pk:<6} user {r.user_id:<6} "
                              f"{r.category} to {r.ends_on}")
