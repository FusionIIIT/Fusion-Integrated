from django.core.management.base import BaseCommand
from django.utils import timezone

from modules.iaa.models import BudgetEntry
from modules.iaa.selectors import policy as policy_selectors


class Command(BaseCommand):
    help = "Report what IAA is missing before people can use it: policy, financial year, budget."

    def handle(self, *args, **options):
        problems = []
        if policy_selectors.current_version() is None:
            problems.append("No policy is in effect: publish one under Configuration.")
        year = policy_selectors.financial_year_on(timezone.localdate())
        if year is None:
            problems.append("No financial year covers today: add one under Configuration.")
        elif not BudgetEntry.objects.filter(financial_year=year).exists():
            problems.append(f"No budget is entered for {year.code}: every check will flag it.")
        if problems:
            for p in problems:
                self.stdout.write(self.style.WARNING(p))
        else:
            self.stdout.write(self.style.SUCCESS("IAA is ready."))
