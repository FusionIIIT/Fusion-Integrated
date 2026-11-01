"""Seeds the baseline entitlements from the problem statement (PS §3)."""
from django.core.management.base import BaseCommand

from modules.leave.domain.categories import DEFAULT_ANNUAL_DAYS
from modules.leave.models import LeavePolicy


class Command(BaseCommand):
    help = "Create any missing leave policy with the baseline annual days"

    def handle(self, *args, **opts):
        for category, days in DEFAULT_ANNUAL_DAYS.items():
            _, created = LeavePolicy.objects.get_or_create(
                category=category.value, defaults={"annual_days": days})
            self.stdout.write(f"{category}: {'created' if created else 'kept'}")
