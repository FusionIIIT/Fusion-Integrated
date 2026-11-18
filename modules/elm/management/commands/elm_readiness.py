from django.core.management.base import BaseCommand
from django.db import connection
from modules.elm.models import CalendarVersion, LeavePolicy

class Command(BaseCommand):
    help = "Report ELM prerequisites without silently inventing missing institute configuration."
    def handle(self, *args, **options):
        problems = []
        tables = set(connection.introspection.table_names())
        if "elm_leave_policy" not in tables:
            problems.append("Database migration missing: run manage.py migrate.")
        else:
            policy = LeavePolicy.objects.filter(key="current").first()
            if not policy:
                problems.append("Current leave policy missing: run manage.py seed_elm_policy.")
            else:
                hierarchy = policy.hierarchy or {}
                if not hierarchy.get("unit_heads"):
                    problems.append("No Unit Head mapping is configured in the current hierarchy.")
                if not hierarchy.get("default_sanctioning") and not hierarchy.get("sanctioning"):
                    problems.append("No higher-sanction hierarchy is configured for SCL/EL/COL/VL.")
            if not CalendarVersion.objects.filter(status="published").exists():
                problems.append("No published holiday/RH/vacation calendar exists.")
        if problems:
            self.stdout.write(self.style.WARNING("ELM is not ready:"))
            for item in problems: self.stdout.write(f"  - {item}")
        else:
            self.stdout.write(self.style.SUCCESS("ELM prerequisites are present."))
