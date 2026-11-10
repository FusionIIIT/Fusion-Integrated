"""Run one scheduled job by hand — the cron fallback, and how it is checked.

    manage.py vh_run_scheduled notifications [--limit N]
    manage.py vh_run_scheduled stays
    manage.py vh_run_scheduled reminders
    manage.py vh_run_scheduled duty
    manage.py vh_run_scheduled status
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from modules.visitor_hostel.models import Booking, NotificationOutbox
from modules.visitor_hostel.services import duty, notifications, stays


class Command(BaseCommand):
    help = "Run a Visitors Hostel scheduled job now, or report whether they run"

    def add_arguments(self, parser):
        parser.add_argument("job", choices=("notifications", "stays", "reminders",
                                            "duty", "status"))
        parser.add_argument("--limit", type=int, default=None)

    def handle(self, *args, **opts):
        job = opts["job"]
        if job == "notifications":
            self.stdout.write(str(notifications.deliver_pending(limit=opts["limit"])))
        elif job == "stays":
            self.stdout.write(str(stays.scan()))
        elif job == "reminders":
            self.stdout.write(str(stays.send_reminders()))
        elif job == "duty":
            self.stdout.write(f"closed {duty.close_lapsed()} lapsed assignment(s)")
        else:
            self._status()

    def _status(self):
        now = timezone.now()
        pending = NotificationOutbox.objects.filter(status="pending")
        oldest = pending.order_by("created_at").values_list("created_at", flat=True).first()
        self.stdout.write(f"  outbox pending   {pending.count()}")
        self.stdout.write(f"  oldest pending   "
                          f"{int((now - oldest).total_seconds()) if oldest else 0}s")
        self.stdout.write(f"  outbox failed    "
                          f"{NotificationOutbox.objects.filter(status='failed').count()}")
        unscanned = (Booking.objects.filter(status__in=("approved", "room_allotted"),
                                            arrival_date__lt=timezone.localdate())
                     .exclude(alerts__kind="no_show").count())
        self.stdout.write(f"  unflagged no-shows {unscanned}"
                          + ("   <- scan_stays is not running" if unscanned else ""))
