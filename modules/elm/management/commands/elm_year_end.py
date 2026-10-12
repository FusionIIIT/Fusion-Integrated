"""Run year-end leave-account processing once for a leave year (EL-UC-020)."""
from django.core.management.base import BaseCommand

from modules.elm.models import ElmSettings
from modules.elm.services import accounts


class Command(BaseCommand):
    help = "Lapse, carry forward and convert leave balances at year end"

    def add_arguments(self, parser):
        parser.add_argument("--year", type=int, default=None,
                            help="Leave year to close (default: the current one)")
        parser.add_argument("--actor", type=int, default=None,
                            help="user_id to record as the actor")

    def handle(self, *args, **options):
        year = options["year"] or ElmSettings.load().current_year
        report = accounts.year_end(year, actor_user_id=options["actor"])
        self.stdout.write(self.style.SUCCESS(f"year {year}: {report}"))
