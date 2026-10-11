import json

from django.core.management.base import BaseCommand

from modules.elm.services.administration import process_sla, process_year_end


class Command(BaseCommand):
    help = "Run ELM pending-task SLA processing or year-end account processing."

    def add_arguments(self, parser):
        parser.add_argument("--year", type=int)

    def handle(self, *args, **options):
        result = (process_year_end(options["year"]) if options["year"] is not None
                  else {"notifications_issued": process_sla()})
        self.stdout.write(json.dumps(result))
