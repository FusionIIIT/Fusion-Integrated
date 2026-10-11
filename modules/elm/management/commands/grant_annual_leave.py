"""Record the annual entitlement for every employee — the manual run of the
scheduled accrual, safe to repeat.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from modules.elm.services import balances as balance_service


class Command(BaseCommand):
    help = "Record annual leave entitlements for a year"

    def add_arguments(self, parser):
        parser.add_argument("--year", type=int, default=None,
                            help="Defaults to the current year")

    def handle(self, *args, **options):
        year = options["year"] or timezone.localdate().year
        granted, already = balance_service.grant_annual_leave(year=year)
        self.stdout.write(self.style.SUCCESS(
            f"leave accrual {year}: {granted} recorded, {already} already present"))
