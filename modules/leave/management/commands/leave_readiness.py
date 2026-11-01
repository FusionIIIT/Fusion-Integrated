"""Is the module ready to be used, and if not, what is missing?

    manage.py leave_readiness

"Not ready" without naming the unmet prerequisite is not an answer, so every
check below reports the specific row or setting that has to exist first.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from modules.leave.domain import categories as cat
from modules.leave.models import HolidayCalendar, LeaveHierarchyStep, LeavePolicy


class Command(BaseCommand):
    help = "Report the unmet prerequisites for the leave module"

    def handle(self, *args, **opts):
        today = timezone.localdate()
        unmet: list[str] = []

        policy = LeavePolicy.objects.filter(is_active=True).first()
        self.stdout.write(f"  policy            "
                          f"{'configured' if policy else 'MISSING'}")
        if policy is None:
            unmet.append("No active leave policy: run 'manage.py seed_leave_policy'.")
        else:
            missing = [c for c in cat.CATEGORIES
                       if c not in (policy.entitlements or {})
                       and c not in cat.ANNUAL_ENTITLEMENT]
            if missing:
                unmet.append(f"No entitlement is configured for {', '.join(missing)}.")

        unit_head = LeaveHierarchyStep.objects.filter(kind="unit_head",
                                                      is_active=True).first()
        final = LeaveHierarchyStep.objects.filter(kind="final_authority",
                                                  is_active=True).first()
        self.stdout.write(f"  unit head step    "
                          f"{unit_head.designation if unit_head else 'MISSING'}")
        self.stdout.write(f"  final authority   "
                          f"{final.designation if final else 'MISSING'}")
        if unit_head is None:
            unmet.append("No Unit Head step is configured, so nothing can be routed.")
        if final is None:
            unmet.append("No final authority is configured, so higher-sanction "
                         "leave cannot be decided.")

        calendar = (HolidayCalendar.objects.filter(published_at__isnull=False,
                                                   effective_from__lte=today)
                    .order_by("-effective_from").first())
        self.stdout.write(f"  holiday calendar  "
                          f"{calendar if calendar else 'MISSING'}")
        if calendar is None:
            unmet.append("No published holiday/RH calendar is effective, so RH "
                         "requests cannot be validated.")

        self.stdout.write(f"  vacation periods  "
                          f"{_vacation_days()} day(s) recorded")
        if not _vacation_periods():
            unmet.append("No academic vacation period is recorded, so VL requests "
                         "cannot be validated.")

        if unmet:
            self.stdout.write("")
            for problem in unmet:
                self.stdout.write(self.style.ERROR(f"  {problem}"))
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS("\n  leave is ready"))


def _vacation_periods():
    from modules.leave.models import AcademicVacationPeriod

    return list(AcademicVacationPeriod.objects.all())


def _vacation_days() -> int:
    return sum((row.end_date - row.start_date).days + 1
               for row in _vacation_periods())
