from django.core.management.base import BaseCommand
from datetime import datetime
from modules.leave.services import run_year_end_processing

class Command(BaseCommand):
    help = 'Run year-end processing for leave management'

    def add_arguments(self, parser):
        parser.add_argument(
            '--year',
            type=int,
            default=datetime.now().year,
            help='Year to process (default: current year)'
        )

    def handle(self, *args, **options):
        year = options['year']
        result = run_year_end_processing(year)
        self.stdout.write(self.style.SUCCESS(f'Year-end processing completed for {year}: {result}'))