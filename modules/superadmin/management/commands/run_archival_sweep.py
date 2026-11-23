from __future__ import annotations

from django.core.management.base import BaseCommand

from modules.superadmin.services.archival import expire_reversibility_sweep


class Command(BaseCommand):
    help = "Manually trigger the reversibility-window expiry sweep (normally run by Celery beat)."

    def handle(self, *args, **options) -> None:
        self.stdout.write("Running archival reversibility expiry sweep …")
        count = expire_reversibility_sweep()
        self.stdout.write(self.style.SUCCESS(f"Done: {count} record(s) finalized as permanent."))
