"""Drain the leave notification outbox, on demand or from the scheduler."""
from __future__ import annotations

from django.core.management.base import BaseCommand

from modules.leave.services import notifications


class Command(BaseCommand):
    help = "Send queued ELM notifications."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--limit", type=int, default=None,
                            help="Maximum rows to attempt in one pass.")

    def handle(self, *args, **options) -> None:
        report = notifications.deliver_pending(limit=options["limit"])
        self.stdout.write(str(report))
        if report.failed:
            self.stderr.write(
                f"{report.failed} message(s) failed; they stay queued until the "
                "attempt cap, then need a manual look.")