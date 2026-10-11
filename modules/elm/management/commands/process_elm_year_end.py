from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from modules.elm.services.leave_management import process_year_end


class SystemActor:
    user_id = 0

    @staticmethod
    def has_permission(code):
        return code == "elm.leave.year_end"


class Command(BaseCommand):
    help = "Process ELM carry-forward, lapse and VL-to-EL year-end rules."

    def add_arguments(self, parser):
        parser.add_argument(
            "--year", type=int, default=timezone.localdate().year - 1,
            help="Completed calendar year to close (defaults to last year).")

    def handle(self, *args, **options):
        result = process_year_end(SystemActor(), options["year"])
        self.stdout.write(
            f"ELM year-end {options['year']}: {result['processed']} account(s) processed.")
        for item in result["exceptions"]:
            self.stderr.write(
                f"EXCEPTION user={item['user_id']} category={item['category']}: "
                f"{item['message']}")
        if result["exceptions"]:
            raise CommandError(
                f"{len(result['exceptions'])} ELM account(s) require review.")
