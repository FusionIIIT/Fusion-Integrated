from django.core.management.base import BaseCommand
from django.utils import timezone

from modules.leave.services import year_end


class Command(BaseCommand):
    help = "Apply ELM year-end lapse, carry-forward, and VL conversion."

    def add_arguments(self, parser):
        parser.add_argument("--year", type=int, default=timezone.now().year)

    def handle(self, *args, **options):
        processed = year_end(year=options["year"])
        self.stdout.write(self.style.SUCCESS(f"Processed {len(processed)} leave accounts."))
