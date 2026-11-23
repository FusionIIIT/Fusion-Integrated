from django.core.management.base import BaseCommand

from modules.oap import registry
from modules.oap.models import ReminderPolicy


class Command(BaseCommand):
    help = "Report OAP prerequisites that are not met yet, and name each one."

    def handle(self, *args, **options):
        unmet = []
        if not ReminderPolicy.objects.exists():
            unmet.append("no reminder policy: run oap_set_reminder_policy, or reminders stay off")
        known = {code for code, _ in registry.PERMISSIONS}
        unmet.extend(
            f"role '{role}' is granted undeclared permission {code}"
            for role, codes in registry.ROLE_GRANTS.items()
            for code in codes
            if code not in known
        )
        if unmet:
            for line in unmet:
                self.stdout.write(f"UNMET: {line}")
            self.stdout.write(self.style.WARNING(f"{len(unmet)} prerequisite(s) unmet."))
        else:
            self.stdout.write(self.style.SUCCESS("OAP is ready."))
