"""Names every prerequisite ELM still lacks before an employee can apply."""
from django.core.management.base import BaseCommand
from django.utils import timezone

from modules.leave.domain.categories import Category
from modules.leave.models import AuthorityRule, HolidayCalendar, LeavePolicy, OrgUnit


class Command(BaseCommand):
    help = "Report what ELM configuration is missing"

    def handle(self, *args, **opts):
        year = timezone.localdate().year
        missing = []
        configured = set(LeavePolicy.objects.values_list("category", flat=True))
        missing += [f"no leave policy for {c}" for c in Category if c not in configured]
        if not HolidayCalendar.objects.filter(year=year, status="published").exists():
            missing.append(f"no published holiday calendar for {year}")
        if not OrgUnit.objects.exclude(head_user_id=None).exists():
            missing.append("no unit has a Unit Head")
        ruled = set(AuthorityRule.objects.values_list("category", flat=True))
        missing += [f"no sanctioning authority for {c}" for c in ("SCL", "EL", "COL", "VL")
                    if c not in ruled]
        for m in missing:
            self.stdout.write(f"  - {m}")
        self.stdout.write("ELM is ready" if not missing else f"{len(missing)} gap(s)")
        if missing:
            raise SystemExit(1)
