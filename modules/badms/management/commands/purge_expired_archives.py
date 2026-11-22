from django.core.management.base import BaseCommand

from modules.badms.tasks import purge_expired_archives


class Command(BaseCommand):
    help = "Scan retention-expired archives and flag them for purge review."

    def handle(self, *args, **options):
        result = purge_expired_archives()
        self.stdout.write(
            self.style.SUCCESS(
                f"Flagged {result.get('flagged_for_review', 0)} expired archives for purge review."
            )
        )
