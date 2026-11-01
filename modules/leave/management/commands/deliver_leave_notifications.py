"""Drain the leave notification outbox by hand (BR-EL-035).

    manage.py deliver_leave_notifications --limit 100
"""
from django.core.management.base import BaseCommand

from modules.leave.models import NotificationOutbox
from modules.leave.services import notifications


class Command(BaseCommand):
    help = "Send the pending leave notifications"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=None,
                            help="Cap this pass, for a cautious first run.")

    def handle(self, *args, **opts):
        before = NotificationOutbox.objects.filter(status="pending").count()
        report = notifications.deliver_pending(limit=opts["limit"])
        after = NotificationOutbox.objects.filter(status="pending").count()
        self.stdout.write(f"  pending before    {before}")
        self.stdout.write(f"  {report}")
        self.stdout.write(f"  pending after     {after}")
