from django.core.management.base import BaseCommand, CommandError

from core.api.exceptions import DomainError
from modules.leave_elm.services import process_configured_year_end


class Command(BaseCommand):
    help = "Run ELM year-end processing when the configured boundary is reached."

    def handle(self, *args, **options):
        try:
            result = process_configured_year_end()
        except DomainError as exc:
            raise CommandError(exc.message) from exc
        if result["due"]:
            self.stdout.write(
                f"processed_employees={result['processed_employees']}",
            )
        else:
            self.stdout.write("Year-end boundary not reached; no balances changed.")
