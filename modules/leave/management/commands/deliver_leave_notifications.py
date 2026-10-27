from django.core.management.base import BaseCommand
from modules.leave.services import deliver_outbox

class Command(BaseCommand):
    help = 'Delivers leave notifications from the outbox'

    def handle(self, *args, **kwargs):
        count_delivered = deliver_outbox()
        self.stdout.write(self.style.SUCCESS(f'Successfully delivered {count_delivered} notifications'))