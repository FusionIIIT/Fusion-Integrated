from django.core.management.base import BaseCommand

from modules.department.services import notifications, roles


class Command(BaseCommand):
    help = "Run each scheduled department task once, as beat would."

    def handle(self, *args, **options):
        applied = roles.apply_transitions()
        report = notifications.deliver_pending()
        self.stdout.write(f"Role transitions applied: {applied}. Notifications: {report}.")
