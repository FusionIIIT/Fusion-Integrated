from django.core.management.base import BaseCommand

from modules.gymkhana.models import NotificationOutbox
from modules.gymkhana.services.notifications import deliver_pending, retry_failed


class Command(BaseCommand):
    help = "Drain the Gymkhana notification outbox."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=500)
        parser.add_argument("--status", action="store_true")
        parser.add_argument("--retry-failed", action="store_true")

    def handle(self, *args, **options):
        if options["status"]:
            for status, _ in NotificationOutbox.Status.choices:
                count = NotificationOutbox.objects.filter(status=status).count()
                self.stdout.write(f"{status}: {count}")
            return
        if options["retry_failed"]:
            count = retry_failed()
            self.stdout.write(self.style.SUCCESS(f"Re-queued {count} notification(s)."))
            return
        report = deliver_pending(limit=options["limit"])
        self.stdout.write(
            f"sent={report['sent']} failed={report['failed']} "
            f"deferred={report['deferred']}"
        )
