from django.core.management.base import BaseCommand

from modules.iaa.services import escalate_overdue


class Command(BaseCommand):
    help = "Run the idempotent IAA approval-timeout check once"

    def handle(self, *args, **options):
        self.stdout.write(str(escalate_overdue()))
