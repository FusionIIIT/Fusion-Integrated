import json

from django.core.management.base import BaseCommand, CommandError

from core.api.exceptions import DomainError
from modules.elm.services.scheduled import close_year, process_sla


class Command(BaseCommand):
    help = "Process ELM pending-only SLA notifications or an idempotent year-end close."

    def add_arguments(self, parser):
        parser.add_argument("operation", choices=["sla", "year-end"])
        parser.add_argument("--year", type=int)

    def handle(self, *args, **options):
        if options["operation"] == "year-end" and options["year"] is None:
            raise CommandError("--year is required for year-end processing.")
        try:
            result = (
                close_year(options["year"]) if options["operation"] == "year-end" else process_sla()
            )
        except DomainError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(result))
        if result.get("exceptions"):
            raise CommandError(
                "Year-end has exceptions; reconcile the reported accounts and rerun."
            )
