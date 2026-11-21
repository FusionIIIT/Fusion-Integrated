"""Run HR-EIS notification creation/delivery without requiring Celery."""

from django.core.management.base import BaseCommand, CommandError

from modules.hreis.models import OutboxEvent
from modules.hreis.services import notifications


class Command(BaseCommand):
    help = "Generate HR reminders, dispatch configured email, or inspect the outbox."

    def add_arguments(self, parser):
        mode = parser.add_mutually_exclusive_group(required=True)
        mode.add_argument("--generate", action="store_true")
        mode.add_argument("--deliver", action="store_true")
        mode.add_argument("--status", action="store_true")
        mode.add_argument("--retry-failed", action="store_true")
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        if options["status"]:
            pending = OutboxEvent.objects.filter(
                event_type="hreis.notification", dispatched_at__isnull=True
            ).count()
            exhausted = OutboxEvent.objects.filter(
                event_type="hreis.notification",
                dispatched_at__isnull=True, attempts__gte=5
            ).count()
            self.stdout.write(f"HR-EIS outbox: {pending} pending, {exhausted} exhausted.")
            return
        if options["retry_failed"]:
            count = OutboxEvent.objects.filter(
                event_type="hreis.notification",
                dispatched_at__isnull=True, attempts__gte=5
            ).update(attempts=0)
            self.stdout.write(f"Requeued {count} exhausted HR-EIS notifications.")
            return
        if options["generate"]:
            a = notifications.create_pending_action_reminders()
            b = notifications.create_policy_deadline_notifications()
            self.stdout.write(f"Generated {a} reminders and {b} policy notices.")
            return
        if options["limit"] < 1:
            raise CommandError("Delivery limit must be positive.")
        sent, failed = notifications.deliver_pending_notifications(limit=options["limit"])
        self.stdout.write(f"Handed {sent} message(s) to email backend; {failed} unresolved.")
