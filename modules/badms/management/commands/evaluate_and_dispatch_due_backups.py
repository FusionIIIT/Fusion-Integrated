from django.core.management.base import BaseCommand

from modules.badms.tasks import evaluate_and_dispatch_due_backups


class Command(BaseCommand):
    help = "Evaluate active backup schedules and dispatch due backup runs."

    def handle(self, *args, **options):
        result = evaluate_and_dispatch_due_backups()
        self.stdout.write(
            self.style.SUCCESS(f"Dispatched {result.get('dispatched', 0)} due backup runs.")
        )
