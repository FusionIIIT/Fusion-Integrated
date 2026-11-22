from django.core.management.base import BaseCommand
from modules.leave.services.notifications import deliver_pending


class Command(BaseCommand):
    help = "Deliver pending Employee Leave Management notifications."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=200)

    def handle(self, *args, **options):
        result = deliver_pending(limit=options["limit"])
        self.stdout.write(" ".join(f"{key}={value}" for key, value in result.items()))
