"""Drain the notification outbox.

Exists as a management command as well as a Celery task so the system works
before a broker does — a cron entry calling this is a perfectly good production
setup for a few hundred emails a day, and it is how the queue gets drained
during an incident when the workers are down.
"""
from django.core.management.base import BaseCommand

from modules.placement.models import NotificationOutbox
from modules.placement.services import notifications


class Command(BaseCommand):
    help = "Send pending placement notifications."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=None,
                            help="Maximum to send in this pass.")
        parser.add_argument("--status", action="store_true",
                            help="Report the queue and exit. Sends nothing.")
        parser.add_argument("--retry-failed", action="store_true",
                            help="Move parked failures back to pending. Use "
                                 "after fixing whatever broke.")

    def handle(self, *args, **opts) -> None:
        if opts["status"]:
            self._status()
            return
        if opts["retry_failed"]:
            n = NotificationOutbox.objects.filter(status="failed").update(
                status="pending", attempts=0, last_error="")
            self.stdout.write(self.style.SUCCESS(f"Re-queued {n} failed row(s)."))
            return

        report = notifications.deliver_pending(limit=opts["limit"])
        self.stdout.write(
            f"  expanded  {report.expanded}\n"
            f"  sent      {report.sent}\n"
            f"  failed    {report.failed}\n"
            f"  capped    {report.skipped_capped}\n"
            f"  deferred  {report.deferred}   (waiting on backoff)\n"
        )
        left = NotificationOutbox.objects.filter(status="pending").count()
        if left:
            self.stdout.write(self.style.WARNING(f"  {left} still pending"))
        else:
            self.stdout.write(self.style.SUCCESS("  queue drained"))

    def _status(self):
        counts = {s: NotificationOutbox.objects.filter(status=s).count()
                  for s, _ in NotificationOutbox.STATUS}
        for status, n in counts.items():
            self.stdout.write(f"  {status:<12} {n}")
        stuck = NotificationOutbox.objects.filter(status="failed")[:5]
        if stuck:
            self.stdout.write("\n  most recent failures:")
            for row in stuck:
                self.stdout.write(f"    {row.topic}: {row.last_error[:90]}")
