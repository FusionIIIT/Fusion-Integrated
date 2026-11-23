"""Run Gymkhana's scheduled work once, by hand."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from modules.gymkhana.services.notifications import deliver_pending
from modules.gymkhana.services.polls import expire_overdue_polls


class Command(BaseCommand):
    help = "Expire overdue polls and send queued notifications now."

    def handle(self, *args, **options):
        self.stdout.write(f"polls expired: {expire_overdue_polls()}")
        self.stdout.write(f"notifications sent: {deliver_pending()}")
