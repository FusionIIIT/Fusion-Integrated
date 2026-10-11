"""Can ELM take its first leave application? Names every unmet prerequisite."""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from modules.elm.domain import policy
from modules.elm.models import CategoryPolicy, SanctionRoute, SlaPolicy, UnitHead
from modules.elm.selectors import accounts as acc


class Command(BaseCommand):
    help = "Report what ELM still needs configured before first use"

    def handle(self, *args, **opts):
        year = timezone.localdate().year
        problems = []
        missing = set(policy.CATEGORIES) - set(
            CategoryPolicy.objects.values_list("category", flat=True))
        if missing:
            problems.append(f"no entitlement for {', '.join(sorted(missing))}")
        if not UnitHead.objects.exists():
            problems.append("no Unit Head configured for any unit")
        have = set(SanctionRoute.objects.values_list("category", "applicant_kind"))
        problems.extend(
            f"no sanctioning path for {cat} of {kind}"
            for cat in sorted(policy.HIGHER_SANCTION)
            for kind in sorted(policy.EMPLOYEE_KINDS)
            if cat in policy.applicable_categories(kind) and (cat, kind) not in have)
        if acc.published_calendar(year) is None:
            problems.append(f"no published holiday/RH calendar for {year}")
        if not SlaPolicy.objects.exists():
            problems.append("no SLA thresholds configured (reminders are off)")
        for p in problems:
            self.stdout.write(f"  - {p}")
        if problems:
            raise CommandError(f"ELM is not ready: {len(problems)} unmet prerequisites")
        self.stdout.write(self.style.SUCCESS("ELM is ready."))
