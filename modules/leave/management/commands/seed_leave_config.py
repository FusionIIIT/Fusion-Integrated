"""Install the current ELM configuration.

    manage.py seed_leave_config --leave-year 2026

BR-EL-030 gives leave-policy parameters no draft/publish lifecycle, so this
command writes the *current* configured values: the baseline entitlements and
counting rules from the problem statement, the configured processing path per
category, and one SLA threshold per task class. Re-running it is idempotent and
revises the current values in place.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from modules.leave.domain import categories as cat
from modules.leave.domain import routing
from modules.leave.models import HierarchyStep, LeavePolicy, SlaThreshold

#: BR-EL-019 — the configured path per category. CL/RH stop at the Unit Head,
#: so no sanction step is configured for them (BR-EL-016).
DEFAULT_ROUTES: dict[str, list[dict]] = {
    cat.CL: [{"step_kind": routing.UNIT_HEAD}],
    cat.RH: [{"step_kind": routing.UNIT_HEAD}],
    cat.SCL: [{"step_kind": routing.UNIT_HEAD},
              {"step_kind": routing.ESTABLISHMENT},
              {"step_kind": routing.SANCTION, "authority": "registrar"}],
    cat.EL: [{"step_kind": routing.UNIT_HEAD},
             {"step_kind": routing.ESTABLISHMENT},
             {"step_kind": routing.SANCTION, "authority": "registrar"}],
    cat.COL: [{"step_kind": routing.UNIT_HEAD},
              {"step_kind": routing.ESTABLISHMENT},
              {"step_kind": routing.SANCTION, "authority": "registrar"}],
    cat.VL: [{"step_kind": routing.UNIT_HEAD},
             {"step_kind": routing.ESTABLISHMENT},
             {"step_kind": routing.SANCTION, "authority": "registrar"}],
}

#: BR-EL-038 — reminder then escalation, per actionable task class.
DEFAULT_SLA = [
    ("unit_head", 48, 96, "notify", ""),
    ("establishment", 48, 96, "notify", ""),
    ("sanction.registrar", 120, 240, "notify", ""),
    ("sanction.director", 120, 240, "notify", ""),
    ("sanction.dean", 120, 240, "notify", ""),
    ("sanction.deputy_registrar_estt", 72, 168, "notify", ""),
    ("substitute", 24, 72, "reassign", "Registrar"),
    ("resumption.review", 72, 168, "notify", ""),
]


class Command(BaseCommand):
    help = "Install the current ELM policy, hierarchy and SLA thresholds."

    def add_arguments(self, parser):
        parser.add_argument("--leave-year", type=int,
                            help="Leave year to configure (default: current).")

    @transaction.atomic
    def handle(self, *args, **options):
        from django.utils import timezone

        leave_year = options["leave_year"] or timezone.localdate().year

        policy, _ = LeavePolicy.objects.update_or_create(
            leave_year=leave_year,
            defaults={
                "label": f"Leave policy {leave_year}",
                "is_current": True,
                "entitlements": {k: str(v) for k, v in cat.ENTITLEMENT.items()},
                "continuous_counting": sorted(cat.CONTINUOUS_COUNTING),
                "half_day_categories": sorted(cat.HALF_DAY_CATEGORIES),
                "category_kinds": {
                    "faculty_only": sorted(cat.FACULTY_ONLY),
                    "non_faculty_only": sorted(cat.NON_FACULTY_ONLY),
                },
                "substitute_required_categories": [],
                "year_end_month": 12,
                "year_end_day": 31,
                "scl_admissibility_note": (
                    "Admissibility of a special purpose is the Sanctioning "
                    "Authority's judgement (BR-EL-004)."),
            })
        LeavePolicy.objects.exclude(pk=policy.pk).filter(is_current=True).update(
            is_current=False)
        self.stdout.write(f"  policy {leave_year} is current")

        for category, steps in DEFAULT_ROUTES.items():
            HierarchyStep.objects.filter(category=category).delete()
            for order, step in enumerate(steps, start=1):
                HierarchyStep.objects.create(
                    category=category, step_order=order,
                    step_kind=step["step_kind"],
                    authority=step.get("authority", ""),
                    label=step["step_kind"].replace("_", " ").title())
        self.stdout.write(f"  {len(DEFAULT_ROUTES)} configured route(s)")

        for task_class, reminder, escalation, action, role in DEFAULT_SLA:
            SlaThreshold.objects.update_or_create(
                task_class=task_class,
                defaults={"reminder_hours": reminder,
                          "escalation_hours": escalation,
                          "escalation_action": action,
                          "escalate_to_role": role, "is_active": True})
        self.stdout.write(f"  {len(DEFAULT_SLA)} SLA threshold(s)")
        self.stdout.write(self.style.SUCCESS("ELM configuration installed"))
