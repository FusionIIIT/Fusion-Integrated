from django.core.management.base import BaseCommand

from modules.lms.services.courses import release_scheduled_items


class Command(BaseCommand):
    help = (
        "Publish scheduled course materials and assignments past their release date "
        "(BR-LMS-006, BR-LMS-011, UC-LMS-015)."
    )

    def handle(self, *args, **options):
        count = release_scheduled_items()
        self.stdout.write(self.style.SUCCESS(f"Released {count} scheduled items."))
