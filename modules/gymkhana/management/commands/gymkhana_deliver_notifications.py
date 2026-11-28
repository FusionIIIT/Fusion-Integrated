"""Run the notification drain once, by hand."""
from django.core.management.base import BaseCommand

from modules.gymkhana.services.notifications import deliver_pending


class Command(BaseCommand):
    help = "Deliver pending Gymkhana notifications now"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=None)

    def handle(self, *args, **opts):
        self.stdout.write(str(deliver_pending(limit=opts["limit"])))
