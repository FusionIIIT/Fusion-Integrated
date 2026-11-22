"""Drain the MMS notification outbox via management command.

Can be run standalone in cron or incident recovery without running Celery.
"""

from django.core.management.base import BaseCommand

from modules.mms.models import NotificationOutbox
from modules.mms.services import notifications


class Command(BaseCommand):
    help = "Send pending MMS notifications."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Maximum to send in this pass.",
        )
        parser.add_argument(
            "--status",
            action="store_true",
            help="Report the queue and exit. Sends nothing.",
        )
        parser.add_argument(
            "--retry-failed",
            action="store_true",
            help="Move parked failures back to pending.",
        )

    def handle(self, *args, **opts) -> None:
        if opts["status"]:
            self._status()
            return

        if opts["retry_failed"]:
            n = NotificationOutbox.objects.filter(status="failed").update(
                status="pending", attempts=0, last_error=""
            )
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
        pending = NotificationOutbox.objects.filter(status="pending").count()
        sending = NotificationOutbox.objects.filter(status="sending").count()
        failed = NotificationOutbox.objects.filter(status="failed").count()
        sent = NotificationOutbox.objects.filter(status="sent").count()
        self.stdout.write(
            f"MMS Notification Outbox Status:\n"
            f"  pending:  {pending}\n"
            f"  sending:  {sending}\n"
            f"  failed:   {failed}\n"
            f"  sent:     {sent}\n"
        )
