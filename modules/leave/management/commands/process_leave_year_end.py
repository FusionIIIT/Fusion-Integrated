from django.core.management.base import BaseCommand, CommandError

from modules.leave.services.accounting import process_year_end


class Command(BaseCommand):
    help = "Close and carry forward Employee Leave Management accounts for a year."

    def add_arguments(self, parser):
        parser.add_argument("year", type=int, help="Leave year being closed")

    def handle(self, *args, **options):
        try:
            result = process_year_end(options["year"])
        except Exception as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(
            "Year-end completed: " + ", ".join(f"{key}={value}" for key, value in result.items())
        ))
