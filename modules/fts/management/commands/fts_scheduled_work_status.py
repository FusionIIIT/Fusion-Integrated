"""Reports status of scheduled work and notification dispatch for FTS."""
from django.core.management.base import BaseCommand
from django.utils import timezone

from modules.fts.models.audit import NotificationEvent
from modules.fts.services.audit import verify_all_files_audit_integrity


class Command(BaseCommand):
    help = "Report status of pending notifications and audit integrity"

    def add_arguments(self, parser):
        parser.add_argument(
            "--max-lag",
            type=int,
            default=0,
            help="Exit 1 if the oldest pending notification is older than this many seconds.",
        )

    def handle(self, *args, **opts):
        now = timezone.now()
        problems = []

        pending = NotificationEvent.objects.filter(delivered=False)
        count = pending.count()
        oldest = pending.order_by("created_at").values_list("created_at", flat=True).first()
        lag = int((now - oldest).total_seconds()) if oldest else 0

        self.stdout.write(f"  notifications pending: {count}")
        self.stdout.write(f"  oldest pending lag:    {lag}s")

        if opts["max_lag"] and lag > opts["max_lag"]:
            problems.append(f"Notification lag {lag}s exceeds threshold {opts['max_lag']}s")

        integrity = verify_all_files_audit_integrity()
        self.stdout.write(f"  audit integrity valid: {integrity}")
        if not integrity:
            problems.append("Audit integrity check failed: sequences or timestamps out of order")

        if problems:
            for p in problems:
                self.stdout.write(self.style.ERROR(f"  {p}"))
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS("  FTS scheduled work looks healthy"))
