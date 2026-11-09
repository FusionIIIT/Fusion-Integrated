"""Management command to manually execute scheduled sweeps."""
from django.core.management.base import BaseCommand

from modules.system_admin.tasks import (
    deliver_notifications,
    send_role_expiry_reminders,
    sweep_expired_archived_user_windows,
    sweep_expired_roles,
    sweep_scheduled_role_activations,
    terminate_inactive_admin_sessions,
)


class Command(BaseCommand):
    help = "Manually execute all System Administrator scheduled sweeps."

    def handle(self, *args, **options):
        self.stdout.write("Running scheduled role activations...")
        sweep_scheduled_role_activations()

        self.stdout.write("Running expired role sweeps...")
        sweep_expired_roles()

        self.stdout.write("Sending role expiry reminders...")
        send_role_expiry_reminders()

        self.stdout.write("Running archived user window finalizations...")
        sweep_expired_archived_user_windows()

        self.stdout.write("Running inactive session terminations...")
        terminate_inactive_admin_sessions()

        self.stdout.write("Draining notification outbox...")
        deliver_notifications()

        self.stdout.write(self.style.SUCCESS("All scheduled sweeps executed successfully."))
