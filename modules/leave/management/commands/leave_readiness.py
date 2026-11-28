import datetime

from django.core.management.base import BaseCommand

from modules.leave.models import Calendar, Policy


class Command(BaseCommand):
    help = "Verify leave policy and calendar readiness for the given year."

    def add_arguments(self, parser):
        parser.add_argument(
            "--year",
            type=int,
            default=datetime.date.today().year,
            help="Year to check readiness for.",
        )

    def handle(self, *args, **options):
        year = options["year"]
        self.stdout.write(f"Checking leave policy readiness for year {year}...")
        gaps = []

        cal = Calendar.objects.filter(year=year).first()
        if not cal:
            gaps.append(f"No calendar found for year {year}")
        else:
            if not cal.published:
                gaps.append(f"Calendar for year {year} is not published")
            if not cal.holidays.exists():
                gaps.append(f"Calendar for year {year} has no holidays configured")

        today = datetime.date(year, 1, 1)
        policy = Policy.objects.filter(
            effective_from__lte=today,
            effective_to__gte=today,
        ).first()

        if not policy:
            gaps.append(f"No policy covering year {year}")
        else:
            if not policy.published:
                gaps.append(f"Policy '{policy.name}' is not published")
            if not policy.category_rules.exists():
                gaps.append(f"Policy '{policy.name}' has no category rules")
            if not policy.authority_rules.exists():
                gaps.append(f"Policy '{policy.name}' has no authority rules")

        if gaps:
            self.stdout.write(
                self.style.ERROR("Leave readiness check FAILED with the following gaps:")
            )
            for g in gaps:
                self.stdout.write(self.style.ERROR(f"  - {g}"))
            raise SystemExit(1)

        self.stdout.write(
            self.style.SUCCESS(f"Leave policy and calendar for year {year} are fully ready.")
        )
