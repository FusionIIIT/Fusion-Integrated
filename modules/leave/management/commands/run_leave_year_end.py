from django.core.management.base import BaseCommand
from django.utils import timezone
from modules.leave.services.year_end import run_year_end_processing


class Command(BaseCommand):
    help = "Run idempotent year-end leave carry-forward and lapse processing."

    def add_arguments(self, parser):
        parser.add_argument("--year", type=int, default=timezone.localdate().year - 1)

    def handle(self, *args, **options):
        count = run_year_end_processing(options["year"])
        self.stdout.write(self.style.SUCCESS(f"Processed year={options['year']} balances={count}"))
