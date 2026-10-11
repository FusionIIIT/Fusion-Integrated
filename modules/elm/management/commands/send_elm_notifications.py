from django.core.management.base import BaseCommand

from modules.elm.services.delivery import deliver


class Command(BaseCommand):
    help = "Deliver pending and retryable ELM email notifications."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        report = deliver(options["limit"])
        self.stdout.write(
            f"ELM notifications: sent={report['sent']} failed={report['failed']}")
