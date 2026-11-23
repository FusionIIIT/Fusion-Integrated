"""Run PMS deadline sweep from CLI (Step 4.8)."""
from __future__ import annotations

from django.core.management.base import BaseCommand

from modules.patents.tasks import pms_sweep_deadlines


class Command(BaseCommand):
    help = "Execute PMS deadline sweep (expirations, overdue reviews, alerts)"

    def handle(self, *args, **options):
        summary = pms_sweep_deadlines()
        self.stdout.write(self.style.SUCCESS(
            f"PMS deadline sweep completed: "
            f"expired={summary['expired']}, "
            f"overdue_reviews={summary['overdue_reviews']}, "
            f"alerts={summary['alerts']}"
        ))
