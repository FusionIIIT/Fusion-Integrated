"""Management command to process periodic System Admin background lifecycle events."""
from django.core.management.base import BaseCommand
from modules.systemadmin.services.role_service import (
    activate_scheduled_roles,
    expire_time_bound_roles,
    send_expiry_reminders,
)
from modules.systemadmin.services.archival_service import (
    finalize_non_restorable_archived_users,
)


class Command(BaseCommand):
    help = "Process background lifecycle events: activate scheduled roles, expire roles, transition archived users, send reminders."

    def handle(self, *args, **options):
        self.stdout.write("Activating scheduled roles reaching start date...")
        activated = activate_scheduled_roles()
        self.stdout.write(f"Activated {activated} scheduled role assignments.")

        self.stdout.write("Expiring time-bound roles reaching end date...")
        expired = expire_time_bound_roles()
        self.stdout.write(f"Expired {expired} role assignments.")

        self.stdout.write("Transitioning archived users past reversibility window to permanent_non_restorable...")
        finalized = finalize_non_restorable_archived_users()
        self.stdout.write(f"Finalized {finalized} archived user records.")

        self.stdout.write("Dispatching upcoming role expiry reminders...")
        reminders = send_expiry_reminders()
        self.stdout.write(f"Dispatched {reminders} role expiry reminders.")

        self.stdout.write(self.style.SUCCESS("Periodic lifecycle processing completed successfully."))
