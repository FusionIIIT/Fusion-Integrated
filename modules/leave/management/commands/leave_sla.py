"""SF-EL-002. Remind, then escalate, whoever a request is waiting on.

Run it on a schedule — every fifteen minutes is ample, since the thresholds are
in hours. Running it more often than that costs one query and changes nothing:
a clock already reminded is not reminded again.
"""
from django.core.management.base import BaseCommand

from modules.leave.models import SlaClock
from modules.leave.services import sla


class Command(BaseCommand):
    help = "Process leave SLA reminders and escalations."

    def add_arguments(self, parser):
        parser.add_argument("--status", action="store_true",
                            help="Report the open clocks and exit. Sends nothing.")

    def handle(self, *args, **opts) -> None:
        if opts["status"]:
            self._status()
            return

        report = sla.process()
        self.stdout.write(
            f"  reminded   {report.reminded}\n"
            f"  escalated  {report.escalated}\n"
            f"  still open {report.still_open}\n"
        )
        if report.escalated:
            self.stdout.write(self.style.WARNING(
                f"  {report.escalated} task(s) passed their deadline"))
        else:
            self.stdout.write(self.style.SUCCESS("  nothing overdue"))

    def _status(self):
        rows = (SlaClock.objects.filter(stopped_at__isnull=True)
                .order_by("escalate_at")[:20])
        if not rows:
            self.stdout.write("  no open clocks")
            return
        for clock in rows:
            flag = "ESCALATED" if clock.escalated_at else (
                "reminded" if clock.reminded_at else "")
            self.stdout.write(
                f"  request {clock.request_id:<6} {clock.state:<38} "
                f"due {clock.escalate_at:%Y-%m-%d %H:%M} {flag}")
