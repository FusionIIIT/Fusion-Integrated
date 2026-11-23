from django.core.management.base import BaseCommand

from modules.lms.tasks import release_due_assignments


class Command(BaseCommand):
    help = (
        "Make up to 50 due scheduled assignments available through the locked transition service."
    )

    def handle(self, **options):
        self.stdout.write(f"Released {release_due_assignments()} assignments.")
