"""Can the Visitors Hostel take its first booking? Names every unmet prerequisite.

    manage.py vh_readiness            exit 1 if anything is unmet
"""
from django.core.management.base import BaseCommand

from modules.visitor_hostel import registry


class Command(BaseCommand):
    help = "Report what the Visitors Hostel module still needs before it can operate"

    def handle(self, *args, **opts):
        unmet = registry.readiness()
        if not unmet:
            self.stdout.write(self.style.SUCCESS("visitor_hostel is ready"))
            return
        self.stdout.write(self.style.ERROR(f"visitor_hostel: {len(unmet)} unmet:"))
        for reason in unmet:
            self.stdout.write(f"  - {reason}")
        raise SystemExit(1)
