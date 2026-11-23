from __future__ import annotations

from django.core.management.base import BaseCommand

from modules.superadmin.services.purge import expire_purge_requests_sweep


class Command(BaseCommand):
    help = "Manually trigger the purge-request expiry sweep (normally run by Celery beat)."

    def handle(self, *args, **options) -> None:
        self.stdout.write("Running purge-request expiry sweep …")
        count = expire_purge_requests_sweep()
        self.stdout.write(self.style.SUCCESS(f"Done: {count} purge request(s) marked expired."))
